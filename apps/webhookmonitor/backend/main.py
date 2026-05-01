import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..","packages"))

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select, delete
from typing import Optional
from datetime import datetime, timezone
import json, uuid, logging, httpx

from backend_core import create_app, get_current_user, get_session, User
from pydantic import BaseModel

logger = logging.getLogger(__name__)

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

class WebhookPrefsUpdate(BaseModel):
    forward_url: str

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
    return {"forward_url": settings.forward_url}

@settings_router.put("/webhook-prefs")
async def update_webhook_prefs(body: WebhookPrefsUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(WebhookSettings).where(WebhookSettings.user_id == user.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = WebhookSettings(user_id=user.id, forward_url=body.forward_url)
    else:
        settings.forward_url = body.forward_url
    session.add(settings)
    await session.flush()
    return {"forward_url": settings.forward_url}

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
    result = await session.execute(select(WebhookRequest).where(WebhookRequest.endpoint_id == ep.id).order_by(WebhookRequest.received_at.desc()).limit(100))
    return [{"id": r.id, "method": r.method, "path": r.path, "headers": json.loads(r.headers_json), "body": r.body, "received_at": r.received_at.isoformat()} for r in result.scalars().all()]

@webhook_router.delete("/requests")
async def delete_requests(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    ep_result = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.user_id == user.id))
    ep = ep_result.scalar_one_or_none()
    if not ep:
        return {"status": "ok"}
    await session.execute(delete(WebhookRequest).where(WebhookRequest.endpoint_id == ep.id))
    await session.flush()
    return {"status": "deleted"}

# --- Background processing ---

async def _persist_and_forward(
    endpoint_id: int,
    user_id: int,
    method: str,
    path: str,
    headers: dict,
    body: str,
):
    """Offloaded task: save to DB + forward to user's URL (fire-and-forget)."""
    from backend_core.database import SessionLocal

    async with SessionLocal() as session:
        # 1. Persist the request
        req = WebhookRequest(
            endpoint_id=endpoint_id,
            method=method,
            path=path,
            headers_json=json.dumps(headers),
            body=body,
        )
        session.add(req)
        await session.commit()
        logger.debug(f"Saved webhook request {req.id} for endpoint {endpoint_id}")

        # 2. Forward if the user configured a forward_url
        settings_result = await session.execute(
            select(WebhookSettings).where(WebhookSettings.user_id == user_id)
        )
        user_settings = settings_result.scalar_one_or_none()

        if user_settings and user_settings.forward_url:
            forward_url = user_settings.forward_url
            # Strip hop-by-hop headers that shouldn't be forwarded
            safe_headers = {
                k: v for k, v in headers.items()
                if k.lower() not in ("host", "content-length", "transfer-encoding", "connection")
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.request(
                        method=method,
                        url=forward_url,
                        headers=safe_headers,
                        content=body.encode("utf-8"),
                    )
                logger.info(f"Forwarded {method} to {forward_url}")
            except Exception as e:
                logger.warning(f"Forward to {forward_url} failed: {e}")


# Public ingestion endpoint
ingestion_router = APIRouter(tags=["ingestion"])

@ingestion_router.api_route("/hook/{slug}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def ingest_webhook(
    slug: str,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    # Quick lookup — only thing done synchronously
    result = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.slug == slug))
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    body = (await request.body()).decode("utf-8", errors="replace")
    headers = dict(request.headers)

    # Offload heavy work (DB write + forwarding) to background
    background_tasks.add_task(
        _persist_and_forward,
        endpoint_id=ep.id,
        user_id=ep.user_id,
        method=request.method,
        path=str(request.url.path),
        headers=headers,
        body=body,
    )

    # Respond immediately — the caller (Stripe, GitHub, etc.) gets a fast 200
    return {"status": "received"}

app = create_app(title="Webhook Monitor", description="Receive, inspect, and replay webhooks", domain_routers=[webhook_router, ingestion_router, settings_router])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)

