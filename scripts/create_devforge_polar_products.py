import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PRODUCTION_POLAR_API_URL = "https://api.polar.sh/v1"
SANDBOX_POLAR_API_URL = "https://sandbox-api.polar.sh/v1"


@dataclass(frozen=True)
class DevForgeApp:
    slug: str
    env_key: str
    name: str
    description: str
    pro_price_cents: int = 999
    team_price_cents: int = 4900


APPS = [
    DevForgeApp(
        slug="filecleaner",
        env_key="FILECLEANER",
        name="File Cleaner",
        description="Upload, process, and clean files in seconds.",
    ),
    DevForgeApp(
        slug="invoicefollow",
        env_key="INVOICEFOLLOW",
        name="Invoice Follow-up",
        description="Track invoices and automate payment reminders.",
    ),
    DevForgeApp(
        slug="pricetrackr",
        env_key="PRICETRACKR",
        name="Price Tracker",
        description="Monitor competitor prices and get instant alerts.",
    ),
    DevForgeApp(
        slug="webhookmonitor",
        env_key="WEBHOOKMONITOR",
        name="Webhook Monitor",
        description="Receive, inspect, and replay webhooks in real time.",
    ),
    DevForgeApp(
        slug="feedbacklens",
        env_key="FEEDBACKLENS",
        name="Feedback Lens",
        description="Local sentiment analysis and deduped feedback triage.",
        pro_price_cents=1900,
        team_price_cents=7900,
    ),
]


def resolve_api_url(server: str = "", api_url: str = "") -> str:
    if api_url.strip():
        return api_url.rstrip("/")
    if server.strip().lower() == "sandbox":
        return SANDBOX_POLAR_API_URL
    return PRODUCTION_POLAR_API_URL


def build_product_payload(
    app_slug: str,
    tier: str,
    name: str,
    description: str,
    price_cents: int,
) -> dict[str, Any]:
    tier_label = "Pro" if tier == "pro" else "Team"
    return {
        "name": f"{name} {tier_label}",
        "description": f"{description} ({tier_label} Plan)",
        "recurring_interval": "month",
        "recurring_interval_count": 1,
        "visibility": "public",
        "metadata": {
            "devforge_app": app_slug,
            "plan_tier": tier,
            "source": "devforge_polar_migration",
        },
        "prices": [
            {
                "amount_type": "fixed",
                "price_currency": "usd",
                "price_amount": price_cents,
            }
        ],
    }


def active_fixed_price_cents(product: dict[str, Any]) -> int | None:
    for price in product.get("prices", []):
        if (
            price.get("amount_type") == "fixed"
            and not price.get("is_archived", False)
        ):
            return price.get("price_amount")
    return None


def build_product_price_update_payload(price_cents: int) -> dict[str, Any]:
    return {
        "prices": [
            {
                "amount_type": "fixed",
                "price_currency": "usd",
                "price_amount": price_cents,
            }
        ]
    }


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "DevForge-Polar-Migration/2.0",
    }


def _request_json(
    method: str,
    url: str,
    token: str,
    *,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if params:
        url = f"{url}?{urlencode(params)}"

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = Request(url, data=data, method=method, headers=_headers(token))
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"Polar API {method} {url} failed: {exc.code} {body}") from exc


def find_existing_product(token: str, app_slug: str, tier: str, api_url: str) -> dict[str, Any] | None:
    try:
        response = _request_json(
            "GET",
            f"{api_url}/products/",
            token,
            params={
                "limit": 100,
                "metadata[devforge_app]": app_slug,
            },
        )
    except Exception as e:
        print(f"Error checking existing product: {e}")
        return None

    for item in response.get("items", []):
        meta = item.get("metadata", {})
        if (
            meta.get("devforge_app") == app_slug
            and meta.get("plan_tier") == tier
            and not item.get("is_archived")
        ):
            return item
    return None


def create_product(token: str, app: DevForgeApp, tier: str, price_cents: int, api_url: str) -> dict[str, Any]:
    payload = build_product_payload(
        app_slug=app.slug,
        tier=tier,
        name=app.name,
        description=app.description,
        price_cents=price_cents,
    )


def update_product_price(token: str, product_id: str, price_cents: int, api_url: str) -> dict[str, Any]:
    return _request_json(
        "PATCH",
        f"{api_url}/products/{product_id}",
        token,
        payload=build_product_price_update_payload(price_cents),
    )
    return _request_json(
        "POST",
        f"{api_url}/products/",
        token,
        payload=payload,
    )


def sync_products(token: str, api_url: str, dry_run: bool = False) -> dict[str, dict[str, str]]:
    results = {}

    for app in APPS:
        results[app.env_key] = {}
        for tier, price_cents in [("pro", app.pro_price_cents), ("team", app.team_price_cents)]:
            existing = find_existing_product(token, app.slug, tier, api_url)
            if existing:
                current_price = active_fixed_price_cents(existing)
                if current_price != price_cents:
                    if dry_run:
                        print(
                            f"Dry-run: Would update {app.name} ({tier}) "
                            f"from {current_price} to {price_cents} cents/mo"
                        )
                    else:
                        print(
                            f"Updating {app.name} ({tier}) "
                            f"from {current_price} to {price_cents} cents/mo..."
                        )
                        existing = update_product_price(
                            token,
                            existing["id"],
                            price_cents,
                            api_url,
                        )
                print(f"Found existing product for {app.name} ({tier}): {existing['id']}")
                results[app.env_key][tier] = existing["id"]
                continue

            if dry_run:
                print(f"Dry-run: Would create product for {app.name} ({tier}) at ${price_cents/100:.2f}/mo")
                results[app.env_key][tier] = f"dry-run-{app.slug}-{tier}"
                continue

            print(f"Creating product for {app.name} ({tier}) at ${price_cents/100:.2f}/mo...")
            try:
                created = create_product(token, app, tier, price_cents, api_url)
                print(f"Created product: {created['id']}")
                results[app.env_key][tier] = created["id"]
            except Exception as e:
                print(f"Failed to create product for {app.name} ({tier}): {e}")
                results[app.env_key][tier] = "error"

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or find DevForge products (Pro and Team) in Polar.")
    parser.add_argument("--dry-run", action="store_true", help="Validate the script without creating products.")
    args = parser.parse_args()

    token = os.environ.get("POLAR_ACCESS_TOKEN")
    if not token and not args.dry_run:
        print("Error: POLAR_ACCESS_TOKEN environment variable is required.", file=sys.stderr)
        return 1

    if args.dry_run and not token:
        print("Warning: Running dry-run without POLAR_ACCESS_TOKEN. Using dummy token.")
        results = {}
        for app in APPS:
            results[app.env_key] = {"pro": f"dry-run-{app.slug}-pro", "team": f"dry-run-{app.slug}-team"}
    else:
        api_url = resolve_api_url(
            server=os.environ.get("POLAR_SERVER", ""),
            api_url=os.environ.get("POLAR_API_URL", ""),
        )
        results = sync_products(token=token or "", api_url=api_url, dry_run=args.dry_run)

    print("\nPolar product sync complete:\n")

    print("Add these env vars to your .env file or production host:\n")
    for app in APPS:
        pro_id = results[app.env_key].get("pro", "error")
        team_id = results[app.env_key].get("team", "error")
        print(f"# {app.name}")
        print(f"POLAR_PRODUCT_ID_{app.env_key}_PRO={pro_id}")
        print(f"POLAR_PRODUCT_ID_{app.env_key}_TEAM={team_id}")
        print(f"NEXT_PUBLIC_POLAR_PRODUCT_ID_{app.env_key}_PRO={pro_id}")
        print(f"NEXT_PUBLIC_POLAR_PRODUCT_ID_{app.env_key}_TEAM={team_id}")
        print()

    print("JSON for settings:")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
