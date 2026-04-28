import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select, delete
from typing import Optional
from datetime import datetime, timezone
import json, uuid

from backend_core import create_app, get_current_user, get_session, User
from pydantic import BaseModel

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
    return {"endpoint_url": f"https://webhookmonitor.io/hook/{ep.slug}"}

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

# Public ingestion endpoint
ingestion_router = APIRouter(tags=["ingestion"])

@ingestion_router.api_route("/hook/{slug}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def ingest_webhook(slug: str, request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.slug == slug))
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    body = (await request.body()).decode("utf-8", errors="replace")
    headers = dict(request.headers)
    req = WebhookRequest(endpoint_id=ep.id, method=request.method, path=str(request.url.path), headers_json=json.dumps(headers), body=body)
    session.add(req)
    await session.flush()
    return {"status": "received", "id": req.id}

app = create_app(title="Webhook Monitor", description="Receive, inspect, and replay webhooks", domain_routers=[webhook_router, ingestion_router, settings_router])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
