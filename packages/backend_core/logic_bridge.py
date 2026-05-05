"""
Logic Bridge — Connects WebhookMonitor with InvoiceFollow.

When WebhookMonitor receives a webhook payload, it can call this bridge
to detect payment events and auto-mark matching invoices as paid.

Usage (from webhookmonitor _persist_and_forward):
    from backend_core.logic_bridge import detect_and_act_on_payment
    await detect_and_act_on_payment(user_id=ep.user_id, headers=headers, body=body)
"""

import logging
import json
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Payment signal detection
# ---------------------------------------------------------------------------

PAYMENT_KEYWORDS = [
    "order_created", "payment_intent.succeeded", "charge.succeeded",
    "checkout.session.completed", "invoice.payment_succeeded",
    "payment.captured", "transaction.completed",
]

AMOUNT_PATTERNS = [
    re.compile(r'"amount[_]?(?:paid|total|gross)?"\s*:\s*([\d.]+)'),
    re.compile(r'"total"\s*:\s*([\d.]+)'),
    re.compile(r'"price"\s*:\s*([\d.]+)'),
]

EMAIL_PATTERNS = [
    re.compile(r'"email"\s*:\s*"([^"]+)"'),
    re.compile(r'"customer_email"\s*:\s*"([^"]+)"'),
    re.compile(r'"billing_email"\s*:\s*"([^"]+)"'),
]


def detect_payment_webhook(payload: str, headers: dict) -> bool:
    """
    Returns True if the payload appears to be a payment confirmation event.
    Checks for known event names and payment-related keywords.
    """
    payload_lower = payload.lower()

    # Check for known payment event names
    for keyword in PAYMENT_KEYWORDS:
        if keyword in payload_lower:
            return True

    # Check headers for Stripe/LemonSqueezy signatures
    header_keys = {k.lower() for k in headers}
    if "stripe-signature" in header_keys or "x-signature" in header_keys:
        # If it's from a payment provider, be more lenient
        if any(kw in payload_lower for kw in ["payment", "charge", "invoice", "order", "subscription"]):
            return True

    return False


def extract_payment_details(payload: str) -> dict:
    """
    Extracts email and amount from a payment webhook payload.
    Returns {"email": str | None, "amount": float | None}
    """
    email: Optional[str] = None
    amount: Optional[float] = None

    for pattern in EMAIL_PATTERNS:
        match = pattern.search(payload)
        if match:
            email = match.group(1).lower().strip()
            break

    for pattern in AMOUNT_PATTERNS:
        match = pattern.search(payload)
        if match:
            try:
                raw = float(match.group(1))
                # Detect if amount is in cents (Stripe uses cents)
                amount = raw / 100 if raw > 1000 else raw
            except ValueError:
                pass
            break

    return {"email": email, "amount": amount}


async def detect_and_act_on_payment(user_id: int, headers: dict, body: str) -> bool:
    """
    Full bridge call: detects if the webhook is a payment and auto-marks
    matching InvoiceFollow invoices as paid.

    Returns True if an invoice was updated.
    """
    if not detect_payment_webhook(body, headers):
        return False

    details = extract_payment_details(body)
    email = details.get("email")
    amount = details.get("amount")

    if not email:
        logger.debug("Logic bridge: payment detected but no email found in payload")
        return False

    try:
        # Import here to avoid circular imports
        from backend_core.database import get_managed_session
        from sqlmodel import select

        async with get_managed_session() as session:
            # Import the Invoice model from invoicefollow
            # We use a string-based query to avoid tight coupling
            from sqlalchemy import text
            query = text("""
                UPDATE invoices
                SET status = 'paid', bot_active = false
                WHERE user_id = :user_id
                  AND LOWER(client_email) = :email
                  AND status != 'paid'
                RETURNING id
            """)
            result = await session.execute(query, {"user_id": user_id, "email": email.lower()})
            updated_ids = result.fetchall()
            await session.commit()

            if updated_ids:
                logger.info(
                    f"Logic bridge: auto-paid {len(updated_ids)} invoice(s) for "
                    f"user {user_id} / email {email} (amount: {amount})"
                )
                return True

    except Exception as e:
        logger.error(f"Logic bridge error: {e}")

    return False
