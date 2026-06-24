import argparse
import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


POLAR_API_URL = "https://api.polar.sh/v1"


@dataclass(frozen=True)
class DevForgeProduct:
    app_slug: str
    env_key: str
    name: str
    description: str
    price_cents: int = 999


PRODUCTS = [
    DevForgeProduct(
        app_slug="filecleaner",
        env_key="FILECLEANER",
        name="File Cleaner",
        description="Upload, process, and clean files in seconds.",
    ),
    DevForgeProduct(
        app_slug="invoicefollow",
        env_key="INVOICEFOLLOW",
        name="Invoice Follow-up",
        description="Track invoices and automate payment reminders.",
    ),
    DevForgeProduct(
        app_slug="pricetrackr",
        env_key="PRICETRACKR",
        name="Price Tracker",
        description="Monitor competitor prices and get instant alerts.",
    ),
    DevForgeProduct(
        app_slug="webhookmonitor",
        env_key="WEBHOOKMONITOR",
        name="Webhook Monitor",
        description="Receive, inspect, and replay webhooks in real time.",
    ),
    DevForgeProduct(
        app_slug="feedbacklens",
        env_key="FEEDBACKLENS",
        name="Feedback Lens",
        description="Local sentiment analysis and deduped feedback triage.",
    ),
]


def build_product_payload(
    app_slug: str,
    name: str,
    description: str,
    price_cents: int,
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "recurring_interval": "month",
        "recurring_interval_count": 1,
        "visibility": "public",
        "metadata": {
            "devforge_app": app_slug,
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


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "DevForge-Polar-Migration/1.0",
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


def find_existing_product(_client: Any, token: str, product: DevForgeProduct) -> dict[str, Any] | None:
    response = _request_json(
        "GET",
        f"{POLAR_API_URL}/products/",
        token,
        params={
            "limit": 100,
            "metadata[devforge_app]": product.app_slug,
        },
    )

    for item in response.get("items", []):
        if item.get("metadata", {}).get("devforge_app") == product.app_slug and not item.get("is_archived"):
            return item
    return None


def create_product(_client: Any, token: str, product: DevForgeProduct) -> dict[str, Any]:
    return _request_json(
        "POST",
        f"{POLAR_API_URL}/products/",
        token,
        payload=build_product_payload(
            app_slug=product.app_slug,
            name=product.name,
            description=product.description,
            price_cents=product.price_cents,
        ),
    )


def sync_products(token: str, dry_run: bool = False) -> list[tuple[DevForgeProduct, str, str]]:
    results = []

    for product in PRODUCTS:
        existing = find_existing_product(None, token, product)
        if existing:
            results.append((product, existing["id"], "existing"))
            continue

        if dry_run:
            results.append((product, "dry-run", "would_create"))
            continue

        created = create_product(None, token, product)
        results.append((product, created["id"], "created"))

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or find DevForge products in Polar.")
    parser.add_argument("--dry-run", action="store_true", help="Validate the script without creating products.")
    args = parser.parse_args()

    token = os.environ.get("POLAR_ACCESS_TOKEN")
    if not token and not args.dry_run:
        raise SystemExit("POLAR_ACCESS_TOKEN is required")

    if args.dry_run and not token:
        results = [(product, "dry-run", "would_create") for product in PRODUCTS]
    else:
        results = sync_products(token=token or "", dry_run=args.dry_run)

    print("\nPolar product sync complete:\n")
    for product, product_id, status in results:
        print(f"{product.name}: {status} ({product_id})")

    print("\nAdd these env vars to Vercel/Render:\n")
    for product, product_id, _status in results:
        if product_id != "dry-run":
            print(f"NEXT_PUBLIC_POLAR_PRODUCT_ID_{product.env_key}={product_id}")
            print(f"POLAR_PRODUCT_ID_{product.env_key}={product_id}")

    print("\nJSON:")
    print(json.dumps({product.env_key: product_id for product, product_id, _ in results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
