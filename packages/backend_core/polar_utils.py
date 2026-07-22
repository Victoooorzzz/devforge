import base64
import hashlib
import hmac
from time import time
from typing import Any


POLAR_ACTIVATION_EVENTS = {
    "order.paid",
    "subscription.active",
    "subscription.uncanceled",
    "subscription.updated",
}

POLAR_DEACTIVATION_EVENTS = {
    "subscription.canceled",
    "subscription.revoked",
}


def resolve_polar_api_url(*, server: str = "", api_url: str = "") -> str:
    if api_url:
        return api_url.rstrip("/")
    if server.strip().lower() == "sandbox":
        return "https://sandbox-api.polar.sh/v1"
    return "https://api.polar.sh/v1"


def build_polar_checkout_payload(
    user_id: int,
    user_email: str,
    product_id: str,
    frontend_url: str,
) -> dict[str, Any]:
    frontend_url = frontend_url.rstrip("/")

    return {
        "product_id": product_id,
        "customer_email": user_email,
        "external_customer_id": str(user_id),
        "metadata": {"user_id": str(user_id)},
        "customer_metadata": {"user_id": str(user_id)},
        "success_url": f"{frontend_url}/dashboard?checkout_id={{CHECKOUT_ID}}",
        "return_url": f"{frontend_url}/dashboard/settings",
    }


def should_activate_for_polar_event(event_type: str) -> bool:
    return event_type in POLAR_ACTIVATION_EVENTS


def should_deactivate_for_polar_event(event_type: str) -> bool:
    return event_type in POLAR_DEACTIVATION_EVENTS


def get_polar_event_user_id(event: dict[str, Any]) -> str | None:
    data = event.get("data") or {}
    customer = data.get("customer") or {}
    metadata = data.get("metadata") or {}

    user_id = customer.get("external_id") or metadata.get("user_id")
    if user_id:
        return str(user_id)

    customer_metadata = customer.get("metadata") or {}
    user_id = customer_metadata.get("user_id")
    return str(user_id) if user_id else None


def get_polar_event_product_id(event: dict[str, Any]) -> str | None:
    data = event.get("data") or {}

    product_id = data.get("product_id")
    if product_id:
        return str(product_id)

    product = data.get("product") or {}
    product_id = product.get("id")
    if product_id:
        return str(product_id)

    products = data.get("products") or []
    if products and isinstance(products[0], dict) and products[0].get("id"):
        return str(products[0]["id"])

    items = data.get("items") or []
    for item in items:
        item_product = item.get("product") if isinstance(item, dict) else None
        if isinstance(item_product, dict) and item_product.get("id"):
            return str(item_product["id"])
        if isinstance(item, dict) and item.get("product_id"):
            return str(item["product_id"])

    return None


def verify_standard_webhook_signature(
    *,
    payload: bytes,
    webhook_id: str | None,
    webhook_timestamp: str | None,
    webhook_signature: str | None,
    secret: str,
    tolerance_seconds: int = 300,
) -> bool:
    if not secret:
        return True
    if not webhook_id or not webhook_timestamp or not webhook_signature:
        return False

    try:
        timestamp = int(webhook_timestamp)
    except ValueError:
        return False

    if abs(time() - timestamp) > tolerance_seconds:
        return False

    secret_bytes = _decode_webhook_secret(secret)
    signed_content = b".".join([
        webhook_id.encode(),
        webhook_timestamp.encode(),
        payload,
    ])
    expected = base64.b64encode(
        hmac.new(secret_bytes, signed_content, hashlib.sha256).digest()
    ).decode()

    signatures = [
        part.split(",", 1)[-1].strip()
        for part in webhook_signature.split(" ")
        if part.strip()
    ]
    return any(hmac.compare_digest(expected, signature) for signature in signatures)


def _decode_webhook_secret(secret: str) -> bytes:
    for prefix in ("polar_whs_", "whsec_"):
        if secret.startswith(prefix):
            secret = secret.removeprefix(prefix)
            break
    else:
        return secret.encode()

    try:
        padding = "=" * (-len(secret) % 4)
        return base64.b64decode(secret + padding, validate=True)
    except (ValueError, base64.binascii.Error):
        return secret.encode()
