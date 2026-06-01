import re
from typing import Any
from urllib.parse import urlparse


APP_SLUGS = (
    "filecleaner",
    "invoicefollow",
    "pricetrackr",
    "webhookmonitor",
    "feedbacklens",
)

_APP_ALIASES = {
    "filecleaner": "filecleaner",
    "filecleanerpro": "filecleaner",
    "invoicefollow": "invoicefollow",
    "invoicefollowup": "invoicefollow",
    "pricetrackr": "pricetrackr",
    "pricetracker": "pricetrackr",
    "webhookmonitor": "webhookmonitor",
    "feedbacklens": "feedbacklens",
}


def normalize_app_slug(value: str | None) -> str | None:
    if not value:
        return None
    compact = re.sub(r"[^a-z0-9]", "", value.lower())
    return _APP_ALIASES.get(compact)


def app_slug_from_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    subdomain = host.split(".", 1)[0]
    return normalize_app_slug(subdomain)


def product_id_map(settings: Any) -> dict[str, str]:
    return {
        "filecleaner": (
            getattr(settings, "polar_product_id_filecleaner", "")
            or getattr(settings, "next_public_polar_product_id_filecleaner", "")
        ),
        "invoicefollow": (
            getattr(settings, "polar_product_id_invoicefollow", "")
            or getattr(settings, "next_public_polar_product_id_invoicefollow", "")
        ),
        "pricetrackr": (
            getattr(settings, "polar_product_id_pricetrackr", "")
            or getattr(settings, "next_public_polar_product_id_pricetrackr", "")
        ),
        "webhookmonitor": (
            getattr(settings, "polar_product_id_webhookmonitor", "")
            or getattr(settings, "next_public_polar_product_id_webhookmonitor", "")
        ),
        "feedbacklens": (
            getattr(settings, "polar_product_id_feedbacklens", "")
            or getattr(settings, "next_public_polar_product_id_feedbacklens", "")
        ),
    }


def resolve_product_id_for_app(settings: Any, app_name: str | None) -> str | None:
    app_slug = normalize_app_slug(app_name)
    if not app_slug:
        return None
    return product_id_map(settings).get(app_slug) or None


def resolve_app_from_product_id(settings: Any, product_id: str | None) -> str | None:
    if not product_id:
        return None
    for app_slug, configured_product_id in product_id_map(settings).items():
        if configured_product_id and configured_product_id == product_id:
            return app_slug
    return None
