import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
from pydantic import BaseModel, ConfigDict, EmailStr, ValidationError, field_validator
from typing import Optional, Literal
from datetime import datetime, date, timezone
import uuid, logging, json, io
import pandas as pd

from backend_core import create_app, get_current_user, get_session, User, require_product_access, get_settings
from backend_core.database import get_managed_session
from backend_core.email_service import send_email
from backend_core.outbox_models import SystemOutbox, InvoiceMagicLink
from backend_core.product_insights import summarize_invoices
from backend_core.worker import register_job_handler

logger = logging.getLogger(__name__)
settings = get_settings()

# SQL migrations needed for new columns on existing DB:
# ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_promise_date DATE;
# ALTER TABLE invoices ADD COLUMN IF NOT EXISTS cron_paused BOOLEAN DEFAULT FALSE;
# ALTER TABLE invoices ADD COLUMN IF NOT EXISTS promise_token VARCHAR;

class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    client_name: str
    client_email: str = Field(default="")
    amount: float
    due_date: date
    status: str = Field(default="pending")
    reminders_sent: int = Field(default=0)
    last_reminder_date: Optional[date] = None
    # Payment promise
    promise_token: Optional[str] = Field(default=None, index=True)
    payment_promise_date: Optional[date] = None
    cron_paused: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InvoiceSettings(SQLModel, table=True):
    __tablename__ = "invoice_settings"
    user_id: int = Field(primary_key=True)
    email_template: str = Field(default="Hola {client_name}, tu factura por {amount} está vencida. Por favor realiza el pago a la brevedad.")


class InvoiceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    client_name: str
    client_email: EmailStr
    amount: float
    due_date: date

    @field_validator("client_name")
    @classmethod
    def client_name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("client_name is required")
        return value.strip()

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("amount must be greater than 0")
        return value


def _clean_import_value(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def _clean_import_amount(value) -> str:
    return _clean_import_value(value).replace("$", "").replace(",", "")


def _parse_invoice_import(content: bytes, filename: str) -> list[InvoiceCreate]:
    if not content:
        raise ValueError("Import file is empty")

    normalized = filename.lower()
    try:
        if normalized.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif normalized.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise ValueError("Unsupported import file. Use CSV or Excel.")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not read invoice import: {exc}") from exc

    required = ["client_name", "client_email", "amount", "due_date"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    df = df.dropna(how="all")
    if df.empty:
        raise ValueError("Import file has no invoice rows")

    invoices: list[InvoiceCreate] = []
    errors: list[str] = []
    for index, row in df.iterrows():
        try:
            invoices.append(InvoiceCreate(
                client_name=_clean_import_value(row["client_name"]),
                client_email=_clean_import_value(row["client_email"]),
                amount=_clean_import_amount(row["amount"]),
                due_date=_clean_import_value(row["due_date"]),
            ))
        except ValidationError as exc:
            fields = ", ".join(str(error["loc"][0]) for error in exc.errors())
            errors.append(f"Row {int(index) + 2}: {fields}")

    if errors:
        raise ValueError("; ".join(errors))

    return invoices


class InvoiceTemplateUpdate(BaseModel):
    email_template: str


invoice_router = APIRouter(prefix="/invoices", tags=["invoices"], dependencies=[Depends(require_product_access("invoicefollow"))])
settings_router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_product_access("invoicefollow"))])
public_router = APIRouter(prefix="/invoices", tags=["public"])

@invoice_router.post("/cron/reminders/enqueue", tags=["cron"])
async def cron_enqueue_reminders(authorization: str | None = Header(default=None)):
    """Endpoint para cron-job.org. Solo encola, no envía correos sincrónicamente."""
    expected = os.getenv("CRON_SECRET")
    if expected and authorization != f"Bearer {expected}":
         raise HTTPException(status_code=401, detail="Unauthorized")
    await enqueue_overdue_reminders()
    return {"status": "success", "task": "overdue_reminders_enqueued"}


@settings_router.get("/invoice-template")
async def get_invoice_template(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(InvoiceSettings).where(InvoiceSettings.user_id == user.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = InvoiceSettings(user_id=user.id)
        session.add(settings)
        await session.flush()
    return {"email_template": settings.email_template}


@settings_router.put("/invoice-template")
async def update_invoice_template(body: InvoiceTemplateUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(InvoiceSettings).where(InvoiceSettings.user_id == user.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = InvoiceSettings(user_id=user.id, email_template=body.email_template)
    else:
        settings.email_template = body.email_template
    session.add(settings)
    await session.flush()
    return {"email_template": settings.email_template}


def _build_email_body(raw_template: str, inv: "Invoice", tone: str, days_overdue: int) -> tuple[str, str]:
    """Returns (subject, html_body) based on tone escalation."""
    base_content = (
        raw_template
        .replace("{amount}", f"${inv.amount:,.2f}")
        .replace("{client_name}", inv.client_name)
        .replace("{due_date}", str(inv.due_date))
    )

    # Include magic link for downloading PDF securely
    import secrets
    from datetime import timedelta
    magic_token = secrets.token_urlsafe(32)
    # This must be inserted to the DB later in the enqueue flow, so we return the token
    
    api_base = os.getenv("NEXT_PUBLIC_API_URL", "https://api.devforgeapp.pro")
    
    # Include payment promise link
    promise_link = ""
    if inv.promise_token:
        promise_link = f"""
        <p style="margin-top:16px;">
          <a href="{api_base}/invoices/promise/{inv.promise_token}"
             style="background:#10B981;color:white;padding:8px 16px;border-radius:6px;text-decoration:none;font-size:14px;">
            Confirmar promesa de pago
          </a>
        </p>"""
        
    download_link = f"""
        <p style="margin-top:16px;">
          <a href="{api_base}/invoices/download?token={magic_token}"
             style="color:#3B82F6;text-decoration:underline;font-size:14px;">
            Descargar PDF de Factura
          </a>
        </p>
    """

    if tone == "friendly":
        subject = f"Recordatorio: Factura pendiente — {inv.client_name}"
        color = "#10B981"
        header = "Recordatorio amistoso"
        intro = f"Han pasado {days_overdue} día(s) desde la fecha de vencimiento."
    elif tone == "urgent":
        subject = f"URGENTE: Pago requerido — {inv.client_name}"
        color = "#F59E0B"
        header = "Aviso urgente de pago"
        intro = f"Su factura lleva <strong>{days_overdue} días</strong> vencida. Por favor regularice su situación."
    else:  # formal / final
        subject = f"AVISO FINAL: Gestión de cobro — {inv.client_name}"
        color = "#EF4444"
        header = "Aviso final de pago"
        intro = f"Su factura lleva <strong>{days_overdue} días</strong> vencida. Si no recibimos pago, procederemos con gestión de cobro formal."

    html_body = f"""
    <div style="font-family:sans-serif;max-width:600px;padding:24px;border:2px solid {color};border-radius:12px;">
      <h2 style="color:{color};margin:0 0 12px;">{header}</h2>
      <p style="color:#555;">{intro}</p>
      <p style="color:#333;">{base_content}</p>
      <table style="width:100%;margin:16px 0;border-collapse:collapse;">
        <tr><td style="padding:6px;color:#888;">Monto:</td><td style="padding:6px;font-weight:bold;">${inv.amount:,.2f}</td></tr>
        <tr><td style="padding:6px;color:#888;">Vencimiento:</td><td style="padding:6px;">{inv.due_date}</td></tr>
        <tr><td style="padding:6px;color:#888;">Días vencida:</td><td style="padding:6px;color:{color};font-weight:bold;">{days_overdue} días</td></tr>
      </table>
      {promise_link}
      {download_link}
    </div>"""

    return subject, html_body, magic_token


async def enqueue_overdue_reminders():
    """Cron job: encola recordatorios con tono escalado según días vencidos."""
    from datetime import timedelta
    async with get_managed_session() as session:
        today = date.today()
        result = await session.execute(
            select(Invoice).where(
                Invoice.status == "pending",
                Invoice.due_date < today,
                Invoice.cron_paused == False,
            )
        )
        overdue_list = result.scalars().all()

        for inv in overdue_list:
            # Anti-spam: solo si han pasado >= 3 días desde el último recordatorio
            if inv.last_reminder_date and (today - inv.last_reminder_date).days < 3:
                continue

            days_overdue = (today - inv.due_date).days

            # Escalar tono según días vencidos
            if days_overdue <= 7:
                tone = "friendly"
            elif days_overdue <= 15:
                tone = "urgent"
            else:
                tone = "formal"

            # Obtener template del usuario
            settings_res = await session.execute(
                select(InvoiceSettings).where(InvoiceSettings.user_id == inv.user_id)
            )
            user_settings = settings_res.scalar_one_or_none()
            raw_template = user_settings.email_template if user_settings else "Hola {client_name}, tu factura por {amount} está vencida."

            subject, html_body, magic_token = _build_email_body(raw_template, inv, tone, days_overdue)

            logger.info(f"Encolando recordatorio [{tone}] para factura {inv.id} → {inv.client_email}")
            
            # Guardar magic link para descarga
            ml = InvoiceMagicLink(
                token=magic_token,
                invoice_id=str(inv.id),
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            session.add(ml)
            
            # Encolar envío
            job = SystemOutbox(
                app_name="invoicefollow",
                job_type="send_email",
                payload={"to": inv.client_email, "subject": subject, "html_body": html_body},
                priority=3
            )
            session.add(job)

            inv.reminders_sent += 1
            inv.last_reminder_date = today
            session.add(inv)

        await session.commit()

async def handle_send_email(payload: dict):
    to = payload.get("to")
    subject = payload.get("subject")
    html_body = payload.get("html_body")
    send_email(to=to, subject=subject, html_body=html_body)
    return {"delivered_to": to}

register_job_handler("invoicefollow", "send_email", handle_send_email)


@invoice_router.post("")
async def create_invoice(body: InvoiceCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if not user.has_access:
        raise HTTPException(status_code=403, detail="Active subscription or trial required")
    inv = Invoice(
        user_id=user.id,
        client_name=body.client_name,
        client_email=body.client_email,
        amount=body.amount,
        due_date=body.due_date,
        promise_token=uuid.uuid4().hex,
    )
    session.add(inv)
    await session.flush()
    await session.refresh(inv)
    return inv


@invoice_router.post("/import-csv")
async def import_invoices(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    file_size = file.size or 0
    if file_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Invoice import is limited to 5MB")

    filename = file.filename or "invoices.csv"
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in {"csv", "xlsx", "xls"}:
        raise HTTPException(status_code=400, detail="Use CSV or Excel for invoice import")

    try:
        payloads = _parse_invoice_import(await file.read(), filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    invoices = [
        Invoice(
            user_id=user.id,
            client_name=payload.client_name,
            client_email=str(payload.client_email),
            amount=payload.amount,
            due_date=payload.due_date,
            promise_token=uuid.uuid4().hex,
        )
        for payload in payloads
    ]

    for invoice in invoices:
        session.add(invoice)
    await session.flush()
    for invoice in invoices:
        await session.refresh(invoice)

    return {"created": len(invoices), "invoices": invoices}


@invoice_router.get("/list")
async def list_invoices(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Invoice).where(Invoice.user_id == user.id).order_by(Invoice.due_date))
    return result.scalars().all()


@invoice_router.get("/summary")
async def invoice_summary(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Invoice).where(Invoice.user_id == user.id))
    return summarize_invoices(result.scalars().all())


@invoice_router.put("/{invoice_id}/mark-paid")
async def mark_paid(invoice_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == user.id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv.status = "paid"
    inv.cron_paused = False
    session.add(inv)
    await session.flush()
    return {"status": "paid"}


@invoice_router.put("/{invoice_id}/pause-reminders")
async def pause_reminders(invoice_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """Pausa el cron para esta factura (el cliente prometió pagar)."""
    result = await session.execute(select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == user.id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv.cron_paused = True
    inv.payment_promise_date = date.today()
    session.add(inv)
    await session.flush()
    return {"status": "paused", "payment_promise_date": str(inv.payment_promise_date)}


@public_router.get("/promise/{token}")
async def public_promise(token: str, session: AsyncSession = Depends(get_session)):
    """
    Endpoint PÚBLICO (sin auth). El cliente hace clic en el link del email
    para confirmar que pagará. Pausa los recordatorios por 7 días.
    """
    result = await session.execute(select(Invoice).where(Invoice.promise_token == token))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Link inválido o expirado")

    today = date.today()
    inv.cron_paused = True
    inv.payment_promise_date = today
    session.add(inv)
    await session.commit()

    return {
        "message": f"Gracias {inv.client_name}. Hemos registrado tu promesa de pago. Pausaremos los recordatorios por los próximos días.",
        "invoice_id": inv.id,
        "amount": inv.amount,
        "promise_date": str(today),
    }

@public_router.get("/download")
async def download_invoice_magic_link(token: str, session: AsyncSession = Depends(get_session)):
    """Endpoint PÚBLICO para retornar los datos de la factura si el token es válido."""
    res = await session.execute(select(InvoiceMagicLink).where(InvoiceMagicLink.token == token))
    ml = res.scalar_one_or_none()
    
    if not ml or ml.used or ml.expires_at < datetime.utcnow():
        raise HTTPException(status_code=403, detail="Link expirado o inválido")
        
    inv_res = await session.execute(select(Invoice).where(Invoice.id == int(ml.invoice_id)))
    inv = inv_res.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
        
    ml.used = True
    session.add(ml)
    await session.commit()
    
    # Retornamos los datos JSON. El frontend de Vercel debe interceptar /invoices/download?token=XYZ
    # Y con estos datos renderiza el PDF client-side
    return inv


@invoice_router.get("/client-scores")
async def client_scores(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """Retorna un score de riesgo por cliente basado en historial de facturas."""
    result = await session.execute(select(Invoice).where(Invoice.user_id == user.id))
    all_invoices = result.scalars().all()

    from collections import defaultdict
    client_map = defaultdict(list)
    for inv in all_invoices:
        key = inv.client_email or inv.client_name
        client_map[key].append(inv)

    scores = []
    for key, invs in client_map.items():
        total = len(invs)
        paid = sum(1 for i in invs if i.status == "paid")
        overdue = sum(1 for i in invs if i.status in ("pending", "overdue") and i.due_date < date.today())
        avg_reminders = sum(i.reminders_sent for i in invs) / total
        has_promise = any(i.payment_promise_date for i in invs)

        # Score 0-100 (100 = máximo riesgo)
        risk_score = min(100, int(
            (overdue / total) * 50 +
            min(avg_reminders, 5) * 8 +
            (0 if paid / total > 0.5 else 20) +
            (10 if not has_promise else 0)
        ))

        scores.append({
            "client_email": invs[0].client_email,
            "client_name": invs[0].client_name,
            "total_invoices": total,
            "paid": paid,
            "overdue": overdue,
            "avg_reminders": round(avg_reminders, 1),
            "risk_score": risk_score,
            "risk_label": "alto" if risk_score >= 60 else ("medio" if risk_score >= 30 else "bajo"),
        })

    scores.sort(key=lambda x: -x["risk_score"])
    return scores


# ---------------------------------------------------------------------------
# AI Tone Generation — Skill: gemini-api-dev
# ---------------------------------------------------------------------------
@invoice_router.post("/{invoice_id}/ai-tone")
async def generate_ai_tone(
    invoice_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Uses Gemini Flash to generate a personalized collection email.
    Takes into account days overdue, amount, debtor history.
    Returns a preview without saving (dry-run).
    """
    invoice = await session.get(Invoice, invoice_id)
    if not invoice or invoice.user_id != user.id:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Compute days overdue
    today = date.today()
    due = date.fromisoformat(str(invoice.due_date))
    days_overdue = max(0, (today - due).days)

    # Get debtor history
    debtor_result = await session.execute(
        select(Invoice).where(Invoice.user_id == user.id, Invoice.client_email == invoice.client_email)
    )
    debtor_invoices = debtor_result.scalars().all()
    total_invoices = len(debtor_invoices)
    paid_on_time = sum(1 for i in debtor_invoices if i.status == "paid" and i.reminders_sent <= 1)

    async def _generate_with_gemini():
        if not settings.gemini_api_key:
            return None
        try:
            from google import genai
            client = genai.Client(api_key=settings.gemini_api_key)
            if days_overdue == 0:
                tone_hint = "cordial y preventivo (la factura vence hoy o pronto)"
            elif days_overdue <= 7:
                tone_hint = "amable pero firme (pocos días de retraso, primera nota)"
            elif days_overdue <= 30:
                tone_hint = "urgente y profesional (más de una semana de retraso)"
            else:
                tone_hint = "formal y serio, mencionando posibles consecuencias legales si aplica (más de 30 días)"

            prompt = f"""Eres un especialista en cobro de facturas. Genera un email de cobro profesional.

Datos de la factura:
- Cliente: {invoice.client_name}
- Monto: ${invoice.amount:.2f}
- Vencimiento: {invoice.due_date}
- Días vencidos: {days_overdue}
- Recordatorios enviados: {invoice.reminders_sent}
- Historial del cliente: {total_invoices} facturas totales, {paid_on_time} pagadas a tiempo

Tono requerido: {tone_hint}

Responde en JSON con exactamente este formato:
{{
  "subject": "asunto del email",
  "greeting": "saludo personalizado",
  "body": "cuerpo del mensaje (2-3 párrafos)",
  "call_to_action": "frase final de acción",
  "tone_label": "cordial|amable|urgente|formal",
  "days_overdue": {days_overdue}
}}"""
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            result = json.loads(response.text)
            result["engine"] = "gemini"
            return result
        except Exception as e:
            logger.warning(f"Gemini AI tone failed: {e}")
            return None

    def _fallback_tone():
        """Template-based fallback when Gemini is unavailable."""
        if days_overdue == 0:
            tone, subject = "cordial", f"Recordatorio amigable — Factura por ${invoice.amount:.2f}"
            body = f"Estimado/a {invoice.client_name}, le recordamos que su factura por ${invoice.amount:.2f} vence hoy. Puede realizar el pago a través de los medios habituales."
        elif days_overdue <= 7:
            tone, subject = "amable", f"Factura pendiente — {days_overdue} días de retraso"
            body = f"Estimado/a {invoice.client_name}, notamos que la factura por ${invoice.amount:.2f} lleva {days_overdue} días vencida. Le agradecemos regularizar a la brevedad posible."
        elif days_overdue <= 30:
            tone, subject = "urgente", f"URGENTE: Factura ${invoice.amount:.2f} — {days_overdue} días vencida"
            body = f"Estimado/a {invoice.client_name}, su factura por ${invoice.amount:.2f} tiene {days_overdue} días de mora. Requerimos su pago inmediato para evitar cargos adicionales."
        else:
            tone, subject = "formal", f"AVISO FINAL: Factura ${invoice.amount:.2f} — {days_overdue} días"
            body = f"De nuestra mayor consideración, Sr./Sra. {invoice.client_name}: Su cuenta presenta una deuda de ${invoice.amount:.2f} con {days_overdue} días de mora. De no regularizar en 48 horas, procederemos según corresponda."
        return {
            "subject": subject,
            "greeting": f"Estimado/a {invoice.client_name},",
            "body": body,
            "call_to_action": "Realizar pago ahora",
            "tone_label": tone,
            "days_overdue": days_overdue,
            "engine": "template",
        }

    result = await _generate_with_gemini()
    if result is None:
        result = _fallback_tone()
    result["invoice_id"] = invoice_id
    result["client_name"] = invoice.client_name
    result["amount"] = invoice.amount
    return result


# ---------------------------------------------------------------------------
# Export endpoint — Skill: backend-architect
# ---------------------------------------------------------------------------
@invoice_router.get("/export")
async def export_invoices(
    format: Literal["csv", "xlsx", "json"] = Query(default="csv"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Export all invoices as CSV, XLSX, or JSON."""
    result = await session.execute(
        select(Invoice).where(Invoice.user_id == user.id).order_by(Invoice.created_at.desc())
    )
    invoices = result.scalars().all()
    rows = [{
        "id": inv.id,
        "client_name": inv.client_name,
        "client_email": inv.client_email,
        "amount": inv.amount,
        "due_date": str(inv.due_date),
        "status": inv.status,
        "reminders_sent": inv.reminders_sent,
        "created_at": inv.created_at.isoformat(),
    } for inv in invoices]

    if format == "json":
        return StreamingResponse(
            io.BytesIO(json.dumps(rows, indent=2).encode()),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=invoicefollow_export.json"}
        )
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    if format == "xlsx":
        df.to_excel(buf, index=False, engine="openpyxl")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "invoicefollow_export.xlsx"
    else:
        df.to_csv(buf, index=False)
        media_type = "text/csv"
        filename = "invoicefollow_export.csv"
    buf.seek(0)
    return StreamingResponse(buf, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})


app = create_app(
    title="Invoice Follow-up",
    description="Track invoices and automate payment reminders",
    domain_routers=[invoice_router, settings_router, public_router]
)

# APScheduler removido para Vercel Serverless

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
