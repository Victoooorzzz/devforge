# packages/backend-core/stripe_handler.py

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from .auth import User, get_current_user
from .config import get_settings
from .database import get_session
from .email_service import send_email

settings = get_settings()
stripe.api_key = settings.stripe_secret_key
logger = logging.getLogger(__name__)

stripe_router = APIRouter(prefix="/stripe", tags=["stripe"])


# --- Schemas ---

class CheckoutRequest(BaseModel):
    price_id: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


# --- Endpoints ---

@stripe_router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    customer_id = user.stripe_customer_id

    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": str(user.id)},
        )
        customer_id = customer.id
        user.stripe_customer_id = customer_id
        session.add(user)
        await session.flush()

    checkout_session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": body.price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{settings.frontend_url}/dashboard?checkout=success",
        cancel_url=f"{settings.frontend_url}/dashboard?checkout=cancelled",
        metadata={"user_id": str(user.id)},
    )

    return CheckoutResponse(checkout_url=checkout_session.url)


@stripe_router.post("/portal", response_model=PortalResponse)
async def create_portal(user: User = Depends(get_current_user)):
    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription found",
        )

    portal_session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.frontend_url}/dashboard/settings",
    )

    return PortalResponse(portal_url=portal_session.url)


# --- Webhook Handler ---

webhook_router = APIRouter(tags=["webhooks"])


@webhook_router.post("/webhooks/stripe")
async def handle_stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    event_type = event["type"]
    event_data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(event_data, session)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(event_data, session)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(event_data, session)
    else:
        logger.info("Unhandled Stripe event type: %s", event_type)

    return {"status": "ok"}


async def _handle_checkout_completed(data: dict, session: AsyncSession) -> None:
    customer_id = data.get("customer")
    if not customer_id:
        return

    result = await session.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if user:
        user.is_active = True
        session.add(user)
        await session.flush()
        logger.info("Activated user %s after checkout", user.email)


async def _handle_subscription_deleted(data: dict, session: AsyncSession) -> None:
    customer_id = data.get("customer")
    if not customer_id:
        return

    result = await session.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if user:
        user.is_active = False
        session.add(user)
        await session.flush()
        logger.info("Deactivated user %s after subscription cancellation", user.email)


async def _handle_payment_failed(data: dict, session: AsyncSession) -> None:
    customer_id = data.get("customer")
    if not customer_id:
        return

    result = await session.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if user and settings.smtp_host:
        await send_email(
            to=user.email,
            subject="Payment Failed - Action Required",
            html_body=f"""
            <div style="font-family: sans-serif; color: #F5F5F5; background: #0A0A0A; padding: 32px;">
                <h2 style="color: #F5F5F5;">Payment Failed</h2>
                <p style="color: #A3A3A3;">
                    We were unable to process your latest payment. Please update your payment
                    method to continue using the service.
                </p>
                <a href="{settings.frontend_url}/dashboard/settings"
                   style="display: inline-block; margin-top: 16px; padding: 12px 24px;
                          background: #6366F1; color: white; text-decoration: none;
                          border-radius: 6px;">
                    Update Payment Method
                </a>
            </div>
            """,
        )
        logger.info("Sent payment failure email to %s", user.email)
