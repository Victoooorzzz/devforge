import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..","packages"))

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select, delete, func
from typing import Optional
from datetime import datetime, timezone, timedelta
import json, uuid, logging, httpx

from backend_core import create_app, get_current_user, get_session, User
from backend_core.database import get_managed_session
from backend_core.email_service import send_email
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# SQL migrations needed for new columns on existing DB:
# ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS expected_interval_minutes INTEGER DEFAULT 0;
# ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS alert_email VARCHAR DEFAULT '';


class WebhookEndpoint(SQLModel, table=True):
    __tablename__ = "webhook_endpoints"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(unique=True, index=True)
    slug: str = Field(unique=True, index=True)


class WebhookRequest(SQLModel, table=True):
    __tablename__ = "webhook_requests"
    id: Optional[int] = Field(default=None, primary_key=True)
    endpoint_id: int = Field(index=True)
    method: str
    path: str
    headers_json: str = "{}"
    body: str = ""
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WebhookSettings(SQLModel, table=True):
    __tablename__ = "webhook_settings"
    user_id: int = Field(primary_key=True)
    forward_url: str = Field(default="")
    expected_interval_minutes: int = Field(default=0)   # 0 = silence check desactivado
    alert_email: str = Field(default="")


class WebhookPrefsUpdate(BaseModel):
    forward_url: str
    expected_interval_minutes: int = 0
    alert_email: str = ""


class RetryPayload(BaseModel):
    payload_override: Optional[str] = None   # JSON string; None = usa el body original


webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])
settings_router = APIRouter(prefix="/settings", tags=["settings"])


@settings_router.get("/webhook-prefs")
async def get_webhook_prefs(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(WebhookSettings).where(WebhookSettings.user_id == user.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = WebhookSettings(user_id=user.id)
        session.add(settings)
        await session.flush()
    return {
        "forward_url": settings.forward_url,
        "expected_interval_minutes": settings.expected_interval_minutes,
        "alert_email": settings.alert_email,
    }


@settings_router.put("/webhook-prefs")
async def update_webhook_prefs(body: WebhookPrefsUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(WebhookSettings).where(WebhookSettings.user_id == user.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = WebhookSettings(user_id=user.id)
    settings.forward_url = body.forward_url
    settings.expected_interval_minutes = body.expected_interval_minutes
    settings.alert_email = body.alert_email
    session.add(settings)
    await session.flush()
    return {
        "forward_url": settings.forward_url,
        "expected_interval_minutes": settings.expected_interval_minutes,
        "alert_email": settings.alert_email,
    }


@webhook_router.get("/endpoint")
async def get_endpoint(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.user_id == user.id))
    ep = result.scalar_one_or_none()
    if not ep:
        ep = WebhookEndpoint(user_id=user.id, slug=uuid.uuid4().hex[:12])
        session.add(ep)
        await session.flush()
        await session.refresh(ep)
    return {"endpoint_url": f"https://webhookmonitor.devforgeapp.pro/hook/{ep.slug}"}


@webhook_router.get("/requests")
async def list_requests(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    ep_result = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.user_id == user.id))
    ep = ep_result.scalar_one_or_none()
    if not ep:
        return []
    result = await session.execute(
        select(WebhookRequest)
        .where(WebhookRequest.endpoint_id == ep.id)
        .order_by(WebhookRequest.received_at.desc())
        .limit(100)
    )
    return [
        {
            "id": r.id,
            "method": r.method,
            "path": r.path,
            "headers": json.loads(r.headers_json),
            "body": r.body,
            "received_at": r.received_at.isoformat(),
        }
        for r in result.scalars().all()
    ]


@webhook_router.delete("/requests")
async def delete_requests(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    ep_result = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.user_id == user.id))
    ep = ep_result.scalar_one_or_none()
    if not ep:
        return {"status": "ok"}
    await session.execute(delete(WebhookRequest).where(WebhookRequest.endpoint_id == ep.id))
    await session.flush()
    return {"status": "deleted"}


@webhook_router.post("/requests/{request_id}/retry")
async def retry_request(
    request_id: int,
    body: RetryPayload,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Reenvía un webhook al forward_url configurado.
    Si se pasa payload_override (JSON string), lo usa en lugar del body original.
    """
    # Verify ownership via endpoint
    ep_result = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.user_id == user.id))
    ep = ep_result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="No endpoint configured")

    req_result = await session.execute(
        select(WebhookRequest).where(
            WebhookRequest.id == request_id,
            WebhookRequest.endpoint_id == ep.id,
        )
    )
    req = req_result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    settings_result = await session.execute(select(WebhookSettings).where(WebhookSettings.user_id == user.id))
    ws = settings_result.scalar_one_or_none()
    if not ws or not ws.forward_url:
        raise HTTPException(status_code=400, detail="No forward_url configured in settings")

    payload = body.payload_override if body.payload_override is not None else req.body

    # Validate JSON if provided
    if body.payload_override is not None:
        try:
            json.loads(payload)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    headers = json.loads(req.headers_json)
    safe_headers = {
        k: v for k, v in headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding", "connection")
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(
                method=req.method,
                url=ws.forward_url,
                headers=safe_headers,
                content=payload.encode("utf-8"),
            )
        logger.info(f"Retry {req.method} → {ws.forward_url} | status {response.status_code}")
        return {
            "status": "sent",
            "forward_url": ws.forward_url,
            "response_status": response.status_code,
            "payload_used": "override" if body.payload_override is not None else "original",
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Forward failed: {e}")


# --- Silence detection cron ---

async def check_webhook_silence():
    """
    Cron job: detecta silencio en endpoints con expected_interval_minutes > 0.
    Si el último webhook recibido es más antiguo que el intervalo esperado × 2, envía alerta.
    """
    async with get_managed_session() as session:
        # Get all settings with silence check enabled
        settings_res = await session.execute(
            select(WebhookSettings).where(WebhookSettings.expected_interval_minutes > 0)
        )
        all_settings = settings_res.scalars().all()

        for ws in all_settings:
            if not ws.alert_email:
                continue

            # Get the user's endpoint
            ep_res = await session.execute(
                select(WebhookEndpoint).where(WebhookEndpoint.user_id == ws.user_id)
            )
            ep = ep_res.scalar_one_or_none()
            if not ep:
                continue

            # Find most recent webhook
            last_res = await session.execute(
                select(WebhookRequest)
                .where(WebhookRequest.endpoint_id == ep.id)
                .order_by(WebhookRequest.received_at.desc())
                .limit(1)
            )
            last_req = last_res.scalar_one_or_none()

            now = datetime.now(timezone.utc)
            silence_threshold = timedelta(minutes=ws.expected_interval_minutes * 2)

            if last_req is None:
                # Never received any webhook
                last_received_str = "Nunca"
                is_silent = True
            else:
                age = now - last_req.received_at.replace(tzinfo=timezone.utc) if last_req.received_at.tzinfo is None else now - last_req.received_at
                is_silent = age > silence_threshold
                last_received_str = last_req.received_at.strftime("%Y-%m-%d %H:%M UTC")

            if is_silent:
                logger.warning(f"Silence detected for user {ws.user_id} — last webhook: {last_received_str}")
                send_email(
                    to=ws.alert_email,
                    subject="⚠️ Silencio detectado en tu webhook endpoint",
                    html_body=f"""
                    <div style="font-family:sans-serif;padding:20px;border:2px solid #F59E0B;border-radius:12px;">
                      <h2 style="color:#F59E0B;">⚠️ Alerta de silencio</h2>
                      <p>No se han recibido webhooks en tu endpoint por más de
                         <strong>{ws.expected_interval_minutes * 2} minutos</strong>.</p>
                      <p><strong>Último webhook recibido:</strong> {last_received_str}</p>
                      <p><strong>Intervalo esperado:</strong> cada {ws.expected_interval_minutes} minutos</p>
                      <p>Verifica que tu servicio esté enviando correctamente.</p>
                    </div>
                    """
                )


# --- Background processing ---

async def _persist_and_forward(endpoint_id, user_id, method, path, headers, body):
    async with get_managed_session() as session:
        req = WebhookRequest(
            endpoint_id=endpoint_id,
            method=method,
            path=path,
            headers_json=json.dumps(headers),
            body=body,
        )
        session.add(req)
        await session.commit()

        settings_result = await session.execute(
            select(WebhookSettings).where(WebhookSettings.user_id == user_id)
        )
        user_settings = settings_result.scalar_one_or_none()

        if user_settings and user_settings.forward_url:
            safe_headers = {
                k: v for k, v in headers.items()
                if k.lower() not in ("host", "content-length", "transfer-encoding", "connection")
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.request(
                        method=method,
                        url=user_settings.forward_url,
                        headers=safe_headers,
                        content=body.encode("utf-8"),
                    )
            except Exception as e:
                logger.warning(f"Forward failed: {e}")


ingestion_router = APIRouter(tags=["ingestion"])

@ingestion_router.api_route("/hook/{slug}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def ingest_webhook(
    slug: str,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.slug == slug))
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    body = (await request.body()).decode("utf-8", errors="replace")
    headers = dict(request.headers)

    background_tasks.add_task(
        _persist_and_forward,
        endpoint_id=ep.id,
        user_id=ep.user_id,
        method=request.method,
        path=str(request.url.path),
        headers=headers,
        body=body,
    )
    return {"status": "received"}


app = create_app(
    title="Webhook Monitor",
    description="Receive, inspect, and replay webhooks",
    domain_routers=[webhook_router, ingestion_router, settings_router]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
