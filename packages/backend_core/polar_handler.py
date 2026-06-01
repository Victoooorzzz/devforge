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
    get_polar_event_user_id,
    should_activate_for_polar_event,
    should_deactivate_for_polar_event,
    verify_standard_webhook_signature,
)


settings = get_settings()
logger = logging.getLogger(__name__)

polar_router = APIRouter(prefix="/polar", tags=["polar"])
webhook_router = APIRouter(tags=["webhooks"])

POLAR_API_URL = "https://api.polar.sh/v1"


class PolarCheckoutRequest(BaseModel):
    product_id: str


class PolarCheckoutResponse(BaseModel):
    checkout_url: str


class PolarPortalResponse(BaseModel):
    portal_url: str


def _polar_headers() -> dict[str, str]:
    if not settings.polar_access_token:
        raise HTTPException(status_code=500, detail="Polar is not configured")
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.polar_access_token}",
    }


async def create_polar_checkout(user_id: int, user_email: str, product_id: str):
    payload = build_polar_checkout_payload(
        user_id=user_id,
        user_email=user_email,
        product_id=product_id,
        frontend_url=settings.frontend_url,
    )

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{POLAR_API_URL}/checkouts/", json=payload, headers=_polar_headers())
        if response.status_code not in (200, 201):
            logger.error("Polar checkout API error: %s", response.text)
            raise HTTPException(status_code=500, detail="Failed to create checkout")

        data = response.json()
        return data["url"]


@polar_router.post("/checkout", response_model=PolarCheckoutResponse)
async def create_checkout(
    body: PolarCheckoutRequest,
    user: User = Depends(get_current_user),
):
    url = await create_polar_checkout(user.id, user.email, body.product_id)
    return PolarCheckoutResponse(checkout_url=url)


@polar_router.get("/portal", response_model=PolarPortalResponse)
async def get_portal(user: User = Depends(get_current_user)):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{POLAR_API_URL}/customer-sessions/",
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

    logger.info("Polar webhook received: %s for user %s", event_type, user_id)

    if should_activate_for_polar_event(event_type):
        await _set_user_active(user_id, session, is_active=True)
    elif should_deactivate_for_polar_event(event_type):
        await _set_user_active(user_id, session, is_active=False)

    return {"status": "ok"}


async def _set_user_active(user_id: str | None, session: AsyncSession, is_active: bool):
    if not user_id:
        return

    result = await session.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user:
        user.is_active = is_active
        if is_active:
            user.trial_ends_at = None
        session.add(user)
        await session.flush()
        logger.info("Set user %s active=%s via Polar", user.email, is_active)
