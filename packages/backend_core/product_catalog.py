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

PLAN_SLUGS = ("pro", "team")

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


def normalize_plan_slug(value: str | None) -> str | None:
    if not value:
        return "pro"
    compact = re.sub(r"[^a-z0-9]", "", value.lower())
    if compact in {"pro", "paid"}:
        return "pro"
    if compact == "team":
        return "team"
    return None


def _first_setting(settings: Any, *names: str) -> str:
    for name in names:
        value = getattr(settings, name, "")
        if value:
            return value
    return ""


def product_id_map(settings: Any, plan: str | None = "pro") -> dict[str, str]:
    plan_slug = normalize_plan_slug(plan)
    if plan_slug == "team":
        return {
            app_slug: _first_setting(
                settings,
                f"polar_product_id_{app_slug}_team",
                f"next_public_polar_product_id_{app_slug}_team",
            )
            for app_slug in APP_SLUGS
        }
    if plan_slug == "pro":
        return {
            app_slug: _first_setting(
                settings,
                f"polar_product_id_{app_slug}_pro",
                f"next_public_polar_product_id_{app_slug}_pro",
                f"polar_product_id_{app_slug}",
                f"next_public_polar_product_id_{app_slug}",
            )
            for app_slug in APP_SLUGS
        }
    return {app_slug: "" for app_slug in APP_SLUGS}


def resolve_product_id_for_app(settings: Any, app_name: str | None, plan: str | None = "pro") -> str | None:
    app_slug = normalize_app_slug(app_name)
    if not app_slug:
        return None
    return product_id_map(settings, plan).get(app_slug) or None


def resolve_app_from_product_id(settings: Any, product_id: str | None) -> str | None:
    if not product_id:
        return None
    for plan_slug in PLAN_SLUGS:
        for app_slug, configured_product_id in product_id_map(settings, plan_slug).items():
            if configured_product_id and configured_product_id == product_id:
                return app_slug
    return None


def resolve_plan_from_product_id(settings: Any, product_id: str | None) -> str | None:
    if not product_id:
        return None
    for plan_slug in PLAN_SLUGS:
        for configured_product_id in product_id_map(settings, plan_slug).values():
            if configured_product_id and configured_product_id == product_id:
                return plan_slug
    return None
