import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select, delete
from typing import Optional
from datetime import datetime, timezone, timedelta
import json, uuid, logging, httpx

from backend_core import create_app, get_current_user, get_session, User, require_user_access
from backend_core.database import get_managed_session
from backend_core.email_service import send_email
from backend_core.logic_bridge import detect_and_act_on_payment
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# SQL migrations needed:
# ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS user_id INTEGER;
# ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;
# ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP;
# ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS last_retry_status INTEGER;
# ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS auto_retry_enabled BOOLEAN DEFAULT FALSE;
# ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS expected_interval_minutes INTEGER DEFAULT 0;
# ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS alert_email VARCHAR DEFAULT '';
# ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS auto_retry_enabled BOOLEAN DEFAULT FALSE;


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class WebhookEndpoint(SQLModel, table=True):
    __tablename__ = "webhook_endpoints"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(unique=True, index=True)
    slug: str = Field(unique=True, index=True)


class WebhookRequest(SQLModel, table=True):
    __tablename__ = "webhook_requests"
    id: Optional[int] = Field(default=None, primary_key=True)
    endpoint_id: int = Field(index=True)
    user_id: Optional[int] = Field(default=None, index=True)
    method: str
    path: str
    headers_json: str = "{}"
    body: str = ""
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Exponential backoff retry tracking
    retry_count: int = Field(default=0)
    next_retry_at: Optional[datetime] = None
    last_retry_status: Optional[int] = None
    auto_retry_enabled: bool = Field(default=False)


class WebhookSettings(SQLModel, table=True):
    __tablename__ = "webhook_settings"
    user_id: int = Field(primary_key=True)
    forward_url: str = Field(default="")
    expected_interval_minutes: int = Field(default=0)   # 0 = silence check disabled
    alert_email: str = Field(default="")
    auto_retry_enabled: bool = Field(default=False)     # enable auto exponential backoff


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class WebhookPrefsUpdate(BaseModel):
    forward_url: str = ""
    expected_interval_minutes: int = 0
    alert_email: str = ""
    auto_retry_enabled: bool = False


class RetryPayload(BaseModel):
    payload_override: Optional[str] = None  # JSON string; None = use original body
    schedule_auto_retry: bool = False        # schedule exponential backoff if delivery fails


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])
settings_router = APIRouter(prefix="/settings", tags=["settings"])
ingestion_router = APIRouter(tags=["ingestion"])


@settings_router.get("/webhook-prefs")
async def get_webhook_prefs(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(WebhookSettings).where(WebhookSettings.user_id == user.id))
    ws = result.scalar_one_or_none()
    if not ws:
        ws = WebhookSettings(user_id=user.id)
        session.add(ws)
        await session.flush()
    return {
        "forward_url": ws.forward_url,
        "expected_interval_minutes": ws.expected_interval_minutes,
        "alert_email": ws.alert_email,
        "auto_retry_enabled": ws.auto_retry_enabled,
    }


@webhook_router.post("/config")
async def update_config(
    body: WebhookPrefsUpdate,
    user: User = Depends(require_user_access),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(WebhookSettings).where(WebhookSettings.user_id == user.id))
    ws = result.scalar_one_or_none()
    if not ws:
        ws = WebhookSettings(user_id=user.id)
    ws.forward_url = body.forward_url
    ws.expected_interval_minutes = body.expected_interval_minutes
    ws.alert_email = body.alert_email
    ws.auto_retry_enabled = body.auto_retry_enabled
    session.add(ws)
    await session.flush()
    return {"ok": True}


@webhook_router.get("/config")
async def get_config(
    user: User = Depends(require_user_access),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.user_id == user.id))
    ep = result.scalar_one_or_none()
    if not ep:
        ep = WebhookEndpoint(user_id=user.id, slug=uuid.uuid4().hex[:12])
        session.add(ep)
        await session.flush()
        await session.refresh(ep)
    return {"endpoint_url": f"https://webhookmonitor.devforgeapp.pro/hook/{ep.slug}"}


@webhook_router.get("/logs")
async def list_logs(
    user: User = Depends(require_user_access),
    session: AsyncSession = Depends(get_session)
):
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
            "retry_count": r.retry_count,
            "next_retry_at": r.next_retry_at.isoformat() if r.next_retry_at else None,
            "last_retry_status": r.last_retry_status,
            "auto_retry_enabled": r.auto_retry_enabled,
        }
        for r in result.scalars().all()
    ]


@webhook_router.delete("/requests")
async def delete_requests(
    user: User = Depends(require_user_access),
    session: AsyncSession = Depends(get_session)
):
    ep_result = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.user_id == user.id))
    ep = ep_result.scalar_one_or_none()
    if not ep:
        return {"status": "ok"}
    await session.execute(delete(WebhookRequest).where(WebhookRequest.endpoint_id == ep.id))
    await session.flush()
    return {"status": "deleted", "message": "All logs cleared"}


@webhook_router.post("/requests/{request_id}/retry")
async def retry_request(
    request_id: int,
    body: RetryPayload,
    user: User = Depends(require_user_access),
    session: AsyncSession = Depends(get_session),
):
    """
    Reenvía un webhook al forward_url configurado.
    Si schedule_auto_retry=True, activa exponential backoff automático en caso de fallo.
    Backoff: 1min, 2min, 4min, 8min, 16min (max 5 intentos).
    """
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

    ws_result = await session.execute(select(WebhookSettings).where(WebhookSettings.user_id == user.id))
    ws = ws_result.scalar_one_or_none()
    if not ws or not ws.forward_url:
        raise HTTPException(status_code=400, detail="No forward_url configured in settings")

    payload = body.payload_override if body.payload_override is not None else req.body
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
        req.last_retry_status = response.status_code
        is_success = 200 <= response.status_code < 300

        if body.schedule_auto_retry and not is_success and req.retry_count < 5:
            delay_minutes = 2 ** req.retry_count  # 1, 2, 4, 8, 16 minutes
            req.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
            req.retry_count += 1
            req.auto_retry_enabled = True
        elif is_success:
            req.auto_retry_enabled = False
            req.next_retry_at = None

        session.add(req)
        await session.flush()

        logger.info(f"Retry {req.method} -> {ws.forward_url} | HTTP {response.status_code}")
        return {
            "status": "sent",
            "forward_url": ws.forward_url,
            "response_status": response.status_code,
            "payload_used": "override" if body.payload_override is not None else "original",
            "retry_count": req.retry_count,
            "next_retry_at": req.next_retry_at.isoformat() if req.next_retry_at else None,
        }
    except Exception as e:
        if req.retry_count < 5:
            delay_minutes = 2 ** req.retry_count
            req.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
            req.retry_count += 1
            req.auto_retry_enabled = True
            session.add(req)
            await session.flush()
        raise HTTPException(status_code=502, detail=f"Forward failed: {e}")


# ---------------------------------------------------------------------------
# Cron jobs
# ---------------------------------------------------------------------------

async def check_webhook_silences():
    """
    Cron: detects silence on endpoints with expected_interval_minutes > 0.
    If the last webhook is older than 2x the expected interval, sends an alert email.
    """
    async with get_managed_session() as session:
        settings_res = await session.execute(
            select(WebhookSettings).where(WebhookSettings.expected_interval_minutes > 0)
        )
        all_settings = settings_res.scalars().all()

        for ws in all_settings:
            if not ws.alert_email:
                continue

            ep_res = await session.execute(
                select(WebhookEndpoint).where(WebhookEndpoint.user_id == ws.user_id)
            )
            ep = ep_res.scalar_one_or_none()
            if not ep:
                continue

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
                last_received_str = "Never"
                is_silent = True
            else:
                last_ts = last_req.received_at
                if last_ts.tzinfo is None:
                    last_ts = last_ts.replace(tzinfo=timezone.utc)
                age = now - last_ts
                is_silent = age > silence_threshold
                last_received_str = last_ts.strftime("%Y-%m-%d %H:%M UTC")

            if is_silent:
                logger.warning(f"Silence detected for user {ws.user_id} — last webhook: {last_received_str}")
                try:
                    send_email(
                        to=ws.alert_email,
                        subject="⚠️ Webhook Silence Detected",
                        html_body=f"""
                        <div style="font-family:sans-serif;padding:20px;border:2px solid #F59E0B;border-radius:12px;">
                          <h2 style="color:#F59E0B;">⚠️ Silence Alert</h2>
                          <p>No webhooks received in the last <strong>{ws.expected_interval_minutes * 2} minutes</strong>.</p>
                          <p><strong>Last webhook:</strong> {last_received_str}</p>
                          <p><strong>Expected interval:</strong> every {ws.expected_interval_minutes} minutes</p>
                          <p>Please verify your service is sending correctly.</p>
                        </div>
                        """
                    )
                except Exception as e:
                    logger.error(f"Failed to send silence alert: {e}")


async def process_auto_retries():
    """
    Cron: processes pending exponential backoff retries.
    Picks up webhook requests with auto_retry_enabled=True and next_retry_at <= NOW().
    """
    async with get_managed_session() as session:
        now = datetime.now(timezone.utc)
        pending_res = await session.execute(
            select(WebhookRequest).where(
                WebhookRequest.auto_retry_enabled == True,  # noqa: E712
                WebhookRequest.next_retry_at <= now,
                WebhookRequest.retry_count < 5,
            )
        )
        pending = pending_res.scalars().all()
        logger.info(f"Auto-retry cron: {len(pending)} pending retries")

        for req in pending:
            # Find the user's forward_url
            ep_res = await session.execute(
                select(WebhookEndpoint).where(WebhookEndpoint.id == req.endpoint_id)
            )
            ep = ep_res.scalar_one_or_none()
            if not ep:
                req.auto_retry_enabled = False
                session.add(req)
                continue

            ws_res = await session.execute(
                select(WebhookSettings).where(WebhookSettings.user_id == ep.user_id)
            )
            ws = ws_res.scalar_one_or_none()
            if not ws or not ws.forward_url:
                req.auto_retry_enabled = False
                session.add(req)
                continue

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
                        content=req.body.encode("utf-8"),
                    )
                req.last_retry_status = response.status_code
                is_success = 200 <= response.status_code < 300

                if is_success or req.retry_count >= 4:
                    req.auto_retry_enabled = False
                    req.next_retry_at = None
                else:
                    delay_minutes = 2 ** req.retry_count
                    req.next_retry_at = now + timedelta(minutes=delay_minutes)
                    req.retry_count += 1

            except Exception as e:
                logger.warning(f"Auto-retry failed for request {req.id}: {e}")
                if req.retry_count >= 4:
                    req.auto_retry_enabled = False
                else:
                    req.next_retry_at = now + timedelta(minutes=2 ** req.retry_count)
                    req.retry_count += 1

            session.add(req)

        await session.commit()


async def cleanup_old_logs():
    """
    Cron: deletes webhook request logs older than 30 days.
    Prevents the table from growing indefinitely.
    """
    async with get_managed_session() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        result = await session.execute(
            delete(WebhookRequest).where(WebhookRequest.received_at < cutoff)
        )
        deleted = result.rowcount
        await session.commit()
        logger.info(f"Cleanup cron: deleted {deleted} webhook logs older than 30 days")
        return deleted


@webhook_router.post("/cron/silence", tags=["cron"])
async def cron_silence_check(authorization: str = None):
    """Vercel Cron endpoint — detects silent webhooks."""
    expected = os.getenv("CRON_SECRET")
    if expected and authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    await check_webhook_silences()
    return {"status": "success", "task": "silence_check"}


@webhook_router.post("/cron/process-retries", tags=["cron"])
async def cron_process_retries(authorization: str = None):
    """Vercel Cron endpoint — processes exponential backoff retries."""
    expected = os.getenv("CRON_SECRET")
    if expected and authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    await process_auto_retries()
    return {"status": "success", "task": "process_retries"}


@webhook_router.post("/cron/cleanup", tags=["cron"])
async def cron_cleanup_logs(authorization: str = None):
    """Vercel Cron endpoint — purges webhook logs older than 30 days."""
    expected = os.getenv("CRON_SECRET")
    if expected and authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    deleted = await cleanup_old_logs()
    return {"status": "success", "task": "cleanup", "deleted_count": deleted}


# ---------------------------------------------------------------------------
# Ingestion (public, no auth)
# ---------------------------------------------------------------------------

async def _persist_and_forward(endpoint_id, user_id, method, path, headers, body):
    async with get_managed_session() as session:
        req = WebhookRequest(
            endpoint_id=endpoint_id,
            user_id=user_id,
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
                    fwd_response = await client.request(
                        method=method,
                        url=user_settings.forward_url,
                        headers=safe_headers,
                        content=body.encode("utf-8"),
                    )
                req.last_retry_status = fwd_response.status_code
                # Schedule auto-retry if forward failed and user has it enabled
                if user_settings.auto_retry_enabled and not (200 <= fwd_response.status_code < 300):
                    req.auto_retry_enabled = True
                    req.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=1)
                    req.retry_count = 0
                session.add(req)
                await session.commit()
            except Exception as e:
                logger.warning(f"Forward failed: {e}")
                if user_settings.auto_retry_enabled:
                    req.auto_retry_enabled = True
                    req.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=1)
                    req.retry_count = 0
                    session.add(req)
                    await session.commit()

        # Logic Bridge: check if this is a payment webhook and auto-pay invoices
        try:
            await detect_and_act_on_payment(user_id=user_id, headers=headers, body=body)
        except Exception as e:
            logger.debug(f"Logic bridge check skipped: {e}")


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


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = create_app(
    title="Webhook Monitor",
    description="Real-time monitoring, alerting, and exponential backoff retries for your webhooks",
    domain_routers=[ingestion_router, webhook_router, settings_router]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
