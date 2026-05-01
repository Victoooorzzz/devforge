# packages/backend-core/lemonsqueezy_handler.py

import hmac
import hashlib
import logging
import json
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from .auth import User, get_current_user
from .config import get_settings
from .database import get_session

settings = get_settings()
logger = logging.getLogger(__name__)

ls_router = APIRouter(prefix="/lemonsqueezy", tags=["lemonsqueezy"])
webhook_router = APIRouter(tags=["webhooks"])

LS_API_URL = "https://api.lemonsqueezy.com/v1"

# --- Schemas ---

class CheckoutRequest(BaseModel):
    variant_id: str

class CheckoutResponse(BaseModel):
    checkout_url: str

class PortalResponse(BaseModel):
    portal_url: str

# --- API Interaction ---

async def create_ls_checkout(user: User, variant_id: str):
    headers = {
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
        "Authorization": f"Bearer {settings.lemonsqueezy_api_key}"
    }
    
    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": user.email,
                    "custom": {
                        "user_id": str(user.id)
                    }
                }
            },
            "relationships": {
                "store": {
                    "data": {
                        "type": "stores",
                        "id": str(settings.lemonsqueezy_store_id)
                    }
                },
                "variant": {
                    "data": {
                        "type": "variants",
                        "id": str(variant_id)
                    }
                }
            }
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{LS_API_URL}/checkouts", json=payload, headers=headers)
        if response.status_code != 201:
            logger.error(f"LemonSqueezy API error: {response.text}")
            raise HTTPException(status_code=500, detail="Failed to create checkout")
        
        data = response.json()
        return data["data"]["attributes"]["url"]

# --- Endpoints ---

@ls_router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
):
    url = await create_ls_checkout(user, body.variant_id)
    return CheckoutResponse(checkout_url=url)

@ls_router.get("/portal", response_model=PortalResponse)
async def get_portal(user: User = Depends(get_current_user)):
    if not user.lemonsqueezy_customer_id:
        raise HTTPException(status_code=400, detail="User has no active subscription")
    
    headers = {
        "Accept": "application/vnd.api+json",
        "Authorization": f"Bearer {settings.lemonsqueezy_api_key}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{LS_API_URL}/customers/{user.lemonsqueezy_customer_id}", headers=headers)
        if response.status_code != 200:
            logger.error(f"LemonSqueezy API error: {response.text}")
            raise HTTPException(status_code=500, detail="Failed to get customer portal")
        
        data = response.json()
        portal_url = data["data"]["attributes"]["urls"]["customer_portal"]
        return PortalResponse(portal_url=portal_url)

# --- Webhook Handler ---

@webhook_router.post("/webhooks/lemonsqueezy")
async def handle_ls_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    payload = await request.body()
    signature = request.headers.get("X-Signature")

    if not signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signature")

    # Verify signature
    secret = settings.lemonsqueezy_webhook_secret.encode()
    digest = hmac.new(secret, payload, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(digest, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    data = json.loads(payload)
    event_name = data["meta"]["event_name"]
    attributes = data["data"]["attributes"]
    custom_data = data["meta"].get("custom_data", {})
    user_id = custom_data.get("user_id")

    logger.info(f"LS webhook received: {event_name} for user {user_id}")

    if event_name in ("subscription_created", "subscription_updated", "subscription_resumed"):
        sub_status = attributes.get("status")  # "on_trial", "active", "past_due", "cancelled", "expired"

        if sub_status in ("on_trial", "active"):
            await _activate_user(user_id, attributes, session, is_trial=(sub_status == "on_trial"))
        elif sub_status in ("expired", "cancelled", "unpaid", "past_due"):
            # past_due/unpaid usually means they lost access until payment succeeds
            await _deactivate_user(user_id, session)

    elif event_name in ("subscription_cancelled", "subscription_expired", "subscription_terminated"):
        await _deactivate_user(user_id, session)

    elif event_name == "subscription_payment_success":
        # Ensure user is active if a payment finally went through
        await _activate_user(user_id, attributes, session)

    elif event_name == "subscription_payment_failed":
        # Maybe notify user, but for now just deactivate to be safe
        await _deactivate_user(user_id, session)
    
    return {"status": "ok"}

async def _activate_user(user_id: str, attributes: dict, session: AsyncSession, is_trial: bool = False):
    if not user_id:
        return
    
    result = await session.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user:
        user.is_active = True
        user.lemonsqueezy_customer_id = str(attributes.get("customer_id"))
        # If converting from trial to paid, clear the trial end date
        if not is_trial:
            user.trial_ends_at = None
        session.add(user)
        await session.flush()
        logger.info(f"Activated user {user.email} (trial={is_trial})")

async def _deactivate_user(user_id: str, session: AsyncSession):
    if not user_id:
        return
    
    result = await session.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user:
        user.is_active = False
        session.add(user)
        await session.flush()
        logger.info(f"Deactivated user {user.email} (subscription ended)")
