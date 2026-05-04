import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date, timezone
import uuid, logging

from backend_core import create_app, get_current_user, get_session, User
from backend_core.database import get_managed_session
from backend_core.email_service import send_email

logger = logging.getLogger(__name__)

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InvoiceSettings(SQLModel, table=True):
    __tablename__ = "invoice_settings"
    user_id: int = Field(primary_key=True)
    email_template: str = Field(default="Hola {client_name}, tu factura por {amount} está vencida. Por favor realiza el pago a la brevedad.")


class InvoiceCreate(BaseModel):
    client_name: str
    client_email: str
    amount: float
    due_date: date


class InvoiceTemplateUpdate(BaseModel):
    email_template: str


invoice_router = APIRouter(prefix="/invoices", tags=["invoices"])
settings_router = APIRouter(prefix="/settings", tags=["settings"])


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

    # Include payment promise link
    promise_link = ""
    if inv.promise_token:
        api_base = os.getenv("NEXT_PUBLIC_API_URL", "https://api.devforgeapp.pro")
        promise_link = f"""
        <p style="margin-top:16px;">
          <a href="{api_base}/invoices/promise/{inv.promise_token}"
             style="background:#10B981;color:white;padding:8px 16px;border-radius:6px;text-decoration:none;font-size:14px;">
            Confirmar promesa de pago
          </a>
        </p>"""

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
    </div>"""

    return subject, html_body


async def send_overdue_reminders():
    """Cron job: envía recordatorios con tono escalado según días vencidos."""
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

            subject, html_body = _build_email_body(raw_template, inv, tone, days_overdue)

            logger.info(f"Enviando recordatorio [{tone}] para factura {inv.id} → {inv.client_email}")
            send_email(to=inv.client_email, subject=subject, html_body=html_body)

            inv.reminders_sent += 1
            inv.last_reminder_date = today
            session.add(inv)

        await session.commit()


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


@invoice_router.get("/list")
async def list_invoices(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Invoice).where(Invoice.user_id == user.id).order_by(Invoice.due_date))
    return result.scalars().all()


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


@invoice_router.get("/promise/{token}")
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


app = create_app(
    title="Invoice Follow-up",
    description="Track invoices and automate payment reminders",
    domain_routers=[invoice_router, settings_router]
)

@app.on_event("startup")
async def schedule_reminder_job():
    app.state.scheduler.add_job(
        send_overdue_reminders, "cron", hour=9, minute=0,
        id="invoice_reminder_job", replace_existing=True
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
