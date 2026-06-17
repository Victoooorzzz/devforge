import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select, delete
from typing import Optional, Literal
from datetime import datetime, timezone, timedelta
import json, uuid, logging, httpx, io
import pandas as pd

from backend_core import create_app, get_current_user, get_session, User, require_product_access
from backend_core.database import get_managed_session
from backend_core.email_service import send_email
from backend_core.logic_bridge import detect_and_act_on_payment
from backend_core.outbox_models import SystemOutbox
from backend_core.product_insights import summarize_webhooks
from backend_core.security_utils import is_public_http_url
from backend_core.sensitive_data import mask_sensitive_mapping, mask_sensitive_text
from backend_core.worker import register_job_handler
from pydantic import BaseModel

logger = logging.getLogger(__name__)
MAX_WEBHOOK_BODY_BYTES = 1024 * 1024
MAX_WEBHOOKS_PER_MINUTE = 60

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
    received_at: datetime = Field(default_factory=datetime.utcnow)
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


def _matches_log_status(request: WebhookRequest, status: str) -> bool:
    if status == "all":
        return True
    if status == "failed":
        return request.last_retry_status is not None and request.last_retry_status >= 400
    if status == "successful":
        return request.last_retry_status is not None and 200 <= request.last_retry_status < 300
    if status == "pending":
        return request.last_retry_status is None
    if status == "auto_retry":
        return bool(request.auto_retry_enabled)
    return True


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"], dependencies=[Depends(require_product_access("webhookmonitor"))])
settings_router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_product_access("webhookmonitor"))])
ingestion_router = APIRouter(tags=["ingestion"])
cron_router = APIRouter(prefix="/webhooks", tags=["cron"])


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
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(WebhookSettings).where(WebhookSettings.user_id == user.id))
    ws = result.scalar_one_or_none()
    if not ws:
        ws = WebhookSettings(user_id=user.id)
    if body.forward_url and not is_public_http_url(body.forward_url):
        raise HTTPException(status_code=400, detail="Forward URL must be a public http(s) URL")
    ws.forward_url = body.forward_url
    ws.expected_interval_minutes = body.expected_interval_minutes
    ws.alert_email = body.alert_email
    ws.auto_retry_enabled = body.auto_retry_enabled
    session.add(ws)
    await session.flush()
    return {"ok": True}


@webhook_router.get("/config")
async def get_config(
    user: User = Depends(get_current_user),
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
    status: Literal["all", "failed", "successful", "pending", "auto_retry"] = Query(default="all"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    ep_result = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.user_id == user.id))
    ep = ep_result.scalar_one_or_none()
    if not ep:
        return []
    query = select(WebhookRequest).where(WebhookRequest.endpoint_id == ep.id)
    if status == "failed":
        query = query.where(WebhookRequest.last_retry_status >= 400)
    elif status == "successful":
        query = query.where(WebhookRequest.last_retry_status >= 200, WebhookRequest.last_retry_status < 300)
    elif status == "pending":
        query = query.where(WebhookRequest.last_retry_status == None)  # noqa: E711
    elif status == "auto_retry":
        query = query.where(WebhookRequest.auto_retry_enabled == True)  # noqa: E712
    result = await session.execute(query.order_by(WebhookRequest.received_at.desc()).limit(100))
    requests = [r for r in result.scalars().all() if _matches_log_status(r, status)]
    return [
        {
            "id": r.id,
            "method": r.method,
            "path": r.path,
            "headers": mask_sensitive_mapping(json.loads(r.headers_json)),
            "body": r.body,
            "received_at": r.received_at.isoformat(),
            "retry_count": r.retry_count,
            "next_retry_at": r.next_retry_at.isoformat() if r.next_retry_at else None,
            "last_retry_status": r.last_retry_status,
            "auto_retry_enabled": r.auto_retry_enabled,
        }
        for r in requests
    ]


@webhook_router.get("/summary")
async def webhook_summary(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    ep_result = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.user_id == user.id))
    ep = ep_result.scalar_one_or_none()
    if not ep:
        return summarize_webhooks([])

    result = await session.execute(
        select(WebhookRequest)
        .where(WebhookRequest.endpoint_id == ep.id)
        .order_by(WebhookRequest.received_at.desc())
        .limit(1000)
    )
    return summarize_webhooks(result.scalars().all())


@webhook_router.delete("/requests")
async def delete_requests(
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Encola un job de reenvío en system_outbox.
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
    if not is_public_http_url(ws.forward_url):
        raise HTTPException(status_code=400, detail="Forward URL must be a public http(s) URL")
        
    job = SystemOutbox(
        app_name="webhookmonitor",
        job_type="forward_webhook",
        payload={"request_id": req.id, "payload_override": body.payload_override},
        status="pending",
        max_attempts=6 if body.schedule_auto_retry else 1
    )
    session.add(job)
    await session.commit()
    
    return {
        "status": "queued",
        "message": "Retry job queued successfully in system_outbox"
    }


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

            now = datetime.utcnow()
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



async def cleanup_old_logs():
    """
    Cron: deletes webhook request logs older than 30 days.
    Prevents the table from growing indefinitely.
    """
    async with get_managed_session() as session:
        cutoff = datetime.utcnow() - timedelta(days=30)
        result = await session.execute(
            delete(WebhookRequest).where(WebhookRequest.received_at < cutoff)
        )
        deleted = result.rowcount
        await session.commit()
        logger.info(f"Cleanup cron: deleted {deleted} webhook logs older than 30 days")
        return deleted


@cron_router.post("/cron/silence", tags=["cron"])
async def cron_silence_check(authorization: str | None = Header(default=None)):
    """cron-job.org endpoint — detects silent webhooks."""
    expected = os.getenv("CRON_SECRET")
    if expected and authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    await check_webhook_silences()
    return {"status": "success", "task": "silence_check"}



@cron_router.post("/cron/cleanup", tags=["cron"])
async def cron_cleanup_logs(authorization: str | None = Header(default=None)):
    """cron-job.org endpoint — purges webhook logs older than 30 days."""
    expected = os.getenv("CRON_SECRET")
    if expected and authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    deleted = await cleanup_old_logs()
    return {"status": "success", "task": "cleanup", "deleted_count": deleted}


# ---------------------------------------------------------------------------
# Export logs endpoint — Skill: backend-architect
# ---------------------------------------------------------------------------
@webhook_router.get("/logs/export")
async def export_logs(
    format: Literal["csv", "xlsx", "json"] = Query(default="csv"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Export all webhook request logs as CSV, XLSX, or JSON."""
    ep_result = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.user_id == user.id))
    ep = ep_result.scalar_one_or_none()
    if not ep:
        rows = []
    else:
        result = await session.execute(
            select(WebhookRequest)
            .where(WebhookRequest.endpoint_id == ep.id)
            .order_by(WebhookRequest.received_at.desc())
            .limit(1000)
        )
        requests = result.scalars().all()
        rows = [{
            "id": r.id,
            "method": r.method,
            "path": r.path,
            "headers_preview": json.dumps(mask_sensitive_mapping(json.loads(r.headers_json))),
            "body_preview": mask_sensitive_text(r.body[:200] if r.body else ""),
            "received_at": r.received_at.isoformat(),
            "retry_count": r.retry_count,
            "last_retry_status": r.last_retry_status,
            "auto_retry_enabled": r.auto_retry_enabled,
        } for r in requests]

    if format == "json":
        return StreamingResponse(
            io.BytesIO(json.dumps(rows, indent=2).encode()),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=webhookmonitor_export.json"}
        )
    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    buf = io.BytesIO()
    if format == "xlsx":
        df.to_excel(buf, index=False, engine="openpyxl")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "webhookmonitor_export.xlsx"
    else:
        df.to_csv(buf, index=False)
        media_type = "text/csv"
        filename = "webhookmonitor_export.csv"
    buf.seek(0)
    return StreamingResponse(buf, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})


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
        await session.flush()

        settings_result = await session.execute(
            select(WebhookSettings).where(WebhookSettings.user_id == user_id)
        )
        user_settings = settings_result.scalar_one_or_none()

        if user_settings and user_settings.forward_url:
            job = SystemOutbox(
                app_name="webhookmonitor",
                job_type="forward_webhook",
                payload={"request_id": req.id},
                status="pending",
                max_attempts=6 if user_settings.auto_retry_enabled else 1
            )
            session.add(job)
            
        await session.commit()

        # Logic Bridge: check if this is a payment webhook and auto-pay invoices
        try:
            await detect_and_act_on_payment(user_id=user_id, headers=headers, body=body)
        except Exception as e:
            logger.debug(f"Logic bridge check skipped: {e}")

async def process_webhook_forward(payload: dict):
    request_id = payload.get("request_id")
    payload_override = payload.get("payload_override")
    
    async with get_managed_session() as session:
        req_result = await session.execute(select(WebhookRequest).where(WebhookRequest.id == request_id))
        req = req_result.scalar_one_or_none()
        if not req:
            return {"status": "skipped", "reason": "request not found"}
            
        ws_result = await session.execute(select(WebhookSettings).where(WebhookSettings.user_id == req.user_id))
        ws = ws_result.scalar_one_or_none()
        if not ws or not ws.forward_url:
            return {"status": "skipped", "reason": "no forward url"}
        if not is_public_http_url(ws.forward_url):
            return {"status": "skipped", "reason": "unsafe forward url"}
            
        headers = json.loads(req.headers_json)
        safe_headers = {
            k: v for k, v in headers.items()
            if k.lower() not in ("host", "content-length", "transfer-encoding", "connection")
        }
        
        body_to_send = payload_override if payload_override is not None else req.body
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(
                    method=req.method,
                    url=ws.forward_url,
                    headers=safe_headers,
                    content=body_to_send.encode("utf-8"),
                )
            
            req.last_retry_status = response.status_code
            is_success = 200 <= response.status_code < 300
            
            if not is_success:
                req.retry_count += 1
                session.add(req)
                await session.commit()
                raise Exception(f"Forward returned {response.status_code}")
                
            # success!
            req.auto_retry_enabled = False
            req.next_retry_at = None
            session.add(req)
            await session.commit()
            
            return {"status": "success", "forward_url": ws.forward_url, "response_status": response.status_code}
            
        except httpx.RequestError as e:
            req.retry_count += 1
            session.add(req)
            await session.commit()
            raise e

register_job_handler("webhookmonitor", "forward_webhook", process_webhook_forward)


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

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_WEBHOOK_BODY_BYTES:
                raise HTTPException(status_code=413, detail="Webhook body too large")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid content-length header")

    since = datetime.utcnow() - timedelta(minutes=1)
    count_result = await session.execute(
        select(func.count(WebhookRequest.id)).where(
            WebhookRequest.endpoint_id == ep.id,
            WebhookRequest.received_at >= since,
        )
    )
    recent_count = count_result.scalar_one()
    if recent_count >= MAX_WEBHOOKS_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Webhook rate limit exceeded")

    raw_body = await request.body()
    if len(raw_body) > MAX_WEBHOOK_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Webhook body too large")

    body = raw_body.decode("utf-8", errors="replace")
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
    domain_routers=[ingestion_router, webhook_router, settings_router, cron_router]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
