import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from .auth import User, get_current_user
from .config import get_settings
from .database import get_session
from .polar_utils import (
    build_polar_checkout_payload,
    get_polar_event_product_id,
    get_polar_event_user_id,
    resolve_polar_api_url,
    should_activate_for_polar_event,
    should_deactivate_for_polar_event,
    verify_standard_webhook_signature,
)
from .product_access import set_user_product_access
from .product_catalog import resolve_app_from_product_id, resolve_product_id_for_app


settings = get_settings()
logger = logging.getLogger(__name__)

polar_router = APIRouter(prefix="/polar", tags=["polar"])
webhook_router = APIRouter(tags=["webhooks"])


class PolarCheckoutRequest(BaseModel):
    app_name: str | None = None
    product_id: str | None = None


class PolarCheckoutResponse(BaseModel):
    checkout_url: str


class PolarPortalResponse(BaseModel):
    portal_url: str


def _polar_api_url() -> str:
    return resolve_polar_api_url(
        server=settings.polar_server,
        api_url=settings.polar_api_url,
    )


def _polar_headers() -> dict[str, str]:
    if not settings.polar_access_token:
        raise HTTPException(status_code=500, detail="Polar is not configured")
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.polar_access_token}",
    }


def _checkout_frontend_url(request: Request) -> str:
    origin = request.headers.get("origin", "").rstrip("/")
    allowed_origins = {
        value.strip().rstrip("/")
        for value in settings.allowed_origins.split(",")
        if value.strip()
    }
    if origin and origin in allowed_origins:
        return origin
    return settings.frontend_url


async def create_polar_checkout(
    user_id: int,
    user_email: str,
    product_id: str,
    frontend_url: str | None = None,
):
    payload = build_polar_checkout_payload(
        user_id=user_id,
        user_email=user_email,
        product_id=product_id,
        frontend_url=frontend_url or settings.frontend_url,
    )

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{_polar_api_url()}/checkouts/", json=payload, headers=_polar_headers())
        if response.status_code not in (200, 201):
            logger.error("Polar checkout API error: %s", response.text)
            raise HTTPException(status_code=500, detail="Failed to create checkout")

        data = response.json()
        return data["url"]


@polar_router.post("/checkout", response_model=PolarCheckoutResponse)
async def create_checkout(
    body: PolarCheckoutRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    app_name = body.app_name
    product_id = resolve_product_id_for_app(settings, app_name)

    if not product_id and body.product_id:
        app_name = resolve_app_from_product_id(settings, body.product_id)
        product_id = body.product_id if app_name else None

    if not app_name or not product_id:
        raise HTTPException(status_code=400, detail="Invalid product")

    url = await create_polar_checkout(
        user.id,
        user.email,
        product_id,
        frontend_url=_checkout_frontend_url(request),
    )
    return PolarCheckoutResponse(checkout_url=url)


@polar_router.get("/portal", response_model=PolarPortalResponse)
async def get_portal(user: User = Depends(get_current_user)):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{_polar_api_url()}/customer-sessions/",
            json={"external_customer_id": str(user.id)},
            headers=_polar_headers(),
        )
        if response.status_code not in (200, 201):
            logger.error("Polar customer session API error: %s", response.text)
            raise HTTPException(status_code=500, detail="Failed to get customer portal")

        data = response.json()
        return PolarPortalResponse(portal_url=data["customer_portal_url"])


@webhook_router.post("/webhooks/polar")
async def handle_polar_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    payload = await request.body()

    is_valid = verify_standard_webhook_signature(
        payload=payload,
        webhook_id=request.headers.get("webhook-id"),
        webhook_timestamp=request.headers.get("webhook-timestamp"),
        webhook_signature=request.headers.get("webhook-signature"),
        secret=settings.polar_webhook_secret,
    )
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    event = json.loads(payload)
    event_type = event.get("type", "")
    user_id = get_polar_event_user_id(event)
    product_id = get_polar_event_product_id(event)
    app_name = resolve_app_from_product_id(settings, product_id)

    logger.info("Polar webhook received: %s for user %s", event_type, user_id)

    if should_activate_for_polar_event(event_type):
        await _set_user_active(user_id, session, is_active=True, app_name=app_name, product_id=product_id)
    elif should_deactivate_for_polar_event(event_type):
        await _set_user_active(user_id, session, is_active=False, app_name=app_name, product_id=product_id)

    return {"status": "ok"}


async def _set_user_active(
    user_id: str | None,
    session: AsyncSession,
    is_active: bool,
    app_name: str | None = None,
    product_id: str | None = None,
):
    if not user_id:
        return

    result = await session.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user:
        if app_name:
            await set_user_product_access(
                session=session,
                user=user,
                app_name=app_name,
                polar_product_id=product_id,
                is_active=is_active,
            )
        else:
            user.is_active = is_active
            if is_active:
                user.trial_ends_at = None
            session.add(user)
        await session.flush()
        logger.info("Set user %s active=%s via Polar", user.email, is_active)
