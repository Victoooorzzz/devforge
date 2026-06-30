"""
Real backend smoke E2E for the unified DevForge backend.

This script uses the configured database from .env, creates one isolated test
user, exercises the five product backends through the real FastAPI app, then
removes only rows owned by the test marker.
"""

from __future__ import annotations

import asyncio
import argparse
import base64
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

os.chdir(ROOT)

from apps.feedbacklens.backend.main import FeedbackEntry, FeedbackSettings
from apps.invoicefollow.backend.main import Invoice, InvoiceDetectedDraft, InvoiceSettings
from apps.pricetrackr.backend.main import PriceHistory, TrackedUrl
from apps.webhookmonitor.backend.main import WebhookEndpoint, WebhookRequest, WebhookSettings
from backend_core.auth import User, get_current_user
from backend_core.config import get_settings
from backend_core.database import async_session_factory, create_db_and_tables, get_session
from backend_core.product_access import UserProductAccess
from backend_core.product_catalog import resolve_product_id_for_app, resolve_plan_from_product_id
import backend_core.universal_main as universal_main


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)

APPS = ["filecleaner", "invoicefollow", "pricetrackr", "webhookmonitor", "feedbacklens"]


class E2EFailure(AssertionError):
    pass


def assert_ok(response, label: str) -> dict[str, Any] | None:
    if response.status_code >= 400:
        raise E2EFailure(f"{label}: HTTP {response.status_code} {response.text[:600]}")
    try:
        return response.json()
    except Exception:
        return None


async def cleanup_marker(marker: str) -> None:
    async with async_session_factory() as session:
        user_result = await session.execute(select(User).where(User.email == f"{marker}@devforgeapp.pro"))
        user = user_result.scalar_one_or_none()
        if not user:
            return

        tracker_ids_result = await session.execute(
            select(TrackedUrl.id).where(TrackedUrl.user_id == user.id)
        )
        tracker_ids = [row[0] for row in tracker_ids_result.all()]
        if tracker_ids:
            await session.execute(delete(PriceHistory).where(PriceHistory.tracker_id.in_(tracker_ids)))
        await session.execute(delete(TrackedUrl).where(TrackedUrl.user_id == user.id))

        endpoint_ids_result = await session.execute(
            select(WebhookEndpoint.id).where(WebhookEndpoint.user_id == user.id)
        )
        endpoint_ids = [row[0] for row in endpoint_ids_result.all()]
        if endpoint_ids:
            await session.execute(delete(WebhookRequest).where(WebhookRequest.endpoint_id.in_(endpoint_ids)))
        await session.execute(delete(WebhookEndpoint).where(WebhookEndpoint.user_id == user.id))
        await session.execute(delete(WebhookSettings).where(WebhookSettings.user_id == user.id))

        await session.execute(delete(FeedbackEntry).where(FeedbackEntry.user_id == user.id))
        await session.execute(delete(FeedbackSettings).where(FeedbackSettings.user_id == user.id))

        await session.execute(delete(InvoiceDetectedDraft).where(InvoiceDetectedDraft.user_id == user.id))
        await session.execute(delete(Invoice).where(Invoice.user_id == user.id))
        await session.execute(delete(InvoiceSettings).where(InvoiceSettings.user_id == user.id))

        await session.execute(delete(UserProductAccess).where(UserProductAccess.user_id == user.id))
        await session.delete(user)
        await session.commit()


async def seed_user(marker: str) -> User:
    settings = get_settings()
    await create_db_and_tables()
    await cleanup_marker(marker)

    async with async_session_factory() as session:
        user = User(
            email=f"{marker}@devforgeapp.pro",
            name="Codex Real E2E",
            hashed_password="codex-real-e2e-unused",
            is_active=True,
            is_email_verified=True,
            trial_ends_at=None,
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)

        for app_name in APPS:
            session.add(
                UserProductAccess(
                    user_id=user.id,
                    app_name=app_name,
                    polar_product_id=resolve_product_id_for_app(settings, app_name, "pro"),
                    is_active=True,
                )
            )

        await session.commit()
        await session.refresh(user)
        return user


def install_overrides(user: User) -> None:
    universal_main.app.dependency_overrides.clear()

    async def current_user_override() -> User:
        return user

    async def session_override():
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    universal_main.app.dependency_overrides[get_current_user] = current_user_override
    universal_main.app.dependency_overrides[get_session] = session_override


def verify_plan_catalog() -> dict[str, str]:
    settings = get_settings()
    observed: dict[str, str] = {}
    for app_name in APPS:
        pro_id = resolve_product_id_for_app(settings, app_name, "pro")
        if not pro_id:
            raise E2EFailure(f"{app_name}: missing pro Polar product id")
        observed[f"{app_name}:pro"] = resolve_plan_from_product_id(settings, pro_id)
        team_id = resolve_product_id_for_app(settings, app_name, "team")
        if team_id:
            observed[f"{app_name}:team"] = resolve_plan_from_product_id(settings, team_id)
    if resolve_plan_from_product_id(settings, "") is not None:
        raise E2EFailure("catalog: empty product id should resolve to free")
    return observed


async def run_filecleaner(client: httpx.AsyncClient) -> dict[str, Any]:
    analyze = await client.post(
        "/files/analyze",
        files={"file": ("codex-real.csv", b"name,email\nAda,ada@devforgeapp.pro\n", "text/csv")},
    )
    profile = assert_ok(analyze, "filecleaner analyze")
    if not profile or not profile.get("loadable"):
        raise E2EFailure(f"filecleaner analyze: not loadable {profile}")

    utility = await client.post(
        "/files/utility?output_format=webp&quality=70",
        files={"file": ("tiny.png", PNG_1X1, "image/png")},
    )
    if utility.status_code != 200 or not utility.content:
        raise E2EFailure(f"filecleaner utility: HTTP {utility.status_code} bytes={len(utility.content)}")
    return {
        "profile_rows": profile.get("rows"),
        "utility_bytes": len(utility.content),
        "metadata_removed": utility.headers.get("x-devforge-metadata-removed"),
    }


async def run_invoicefollow(client: httpx.AsyncClient, marker: str) -> dict[str, Any]:
    payload = {
        "client_name": "Codex Real E2E Client",
        "client_email": f"billing+{marker}@devforgeapp.pro",
        "amount": 1200.5,
        "currency": "USD",
        "due_date": (date.today() + timedelta(days=10)).isoformat(),
        "issued_date": date.today().isoformat(),
        "invoice_number": f"{marker}-INV",
        "notes": f"{marker} backend real e2e",
    }
    invoice = assert_ok(await client.post("/invoices", json=payload), "invoicefollow create")
    if not invoice or invoice.get("invoice_number") != payload["invoice_number"]:
        raise E2EFailure(f"invoicefollow create: unexpected payload {invoice}")

    detected = assert_ok(
        await client.post(
            "/invoices/detect-email",
            json={
                "subject": f"Invoice {marker}-EMAIL due soon",
                "body": "Please pay invoice INV-REAL-42 for USD 88.75 due 2026-07-20.",
                "sender_email": f"accounts+{marker}@devforgeapp.pro",
                "sender_name": "Accounts",
                "source": "forward",
                "message_id": f"{marker}-msg",
            },
        ),
        "invoicefollow detect-email",
    )
    if not detected or detected.get("status") != "detected":
        raise E2EFailure(f"invoicefollow detect-email: unexpected payload {detected}")
    return {"invoice_id": invoice["id"], "detected_amount": detected.get("amount")}


async def run_pricetrackr(client: httpx.AsyncClient, marker: str) -> dict[str, Any]:
    tracker = assert_ok(
        await client.post(
            "/trackers",
            json={
                "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
                "label": f"{marker} book price",
                "check_frequency_hours": 24,
            },
        ),
        "pricetrackr create",
    )
    if not tracker or tracker.get("current_price") is None:
        raise E2EFailure(f"pricetrackr create: scraper did not produce price {tracker}")

    history = assert_ok(await client.get(f"/trackers/{tracker['id']}/history"), "pricetrackr history")
    if not history:
        raise E2EFailure("pricetrackr history: expected at least one price point")
    return {"tracker_id": tracker["id"], "price": tracker["current_price"], "history_points": len(history)}


async def run_webhookmonitor(client: httpx.AsyncClient, marker: str) -> dict[str, Any]:
    endpoint = assert_ok(
        await client.post("/webhooks/endpoints", json={"name": f"{marker} endpoint", "methods": ["POST"]}),
        "webhookmonitor create endpoint",
    )
    if not endpoint or "uuid" not in endpoint:
        raise E2EFailure(f"webhookmonitor create endpoint: unexpected payload {endpoint}")

    ingest = assert_ok(
        await client.post(f"/in/{endpoint['uuid']}?codex_marker={marker}", json={"marker": marker, "ok": True}),
        "webhookmonitor ingest",
    )
    if not ingest or ingest.get("status") != "received":
        raise E2EFailure(f"webhookmonitor ingest: unexpected payload {ingest}")

    events = assert_ok(await client.get(f"/webhooks/endpoints/{endpoint['id']}/events"), "webhookmonitor events")
    if not events:
        raise E2EFailure("webhookmonitor events: expected persisted request")
    return {"endpoint_id": endpoint["id"], "request_count": len(events)}


async def run_feedbacklens(client: httpx.AsyncClient, marker: str) -> dict[str, Any]:
    payload = {
        "texts": [
            f"{marker} Checkout broke after payment and I need help urgently.",
            f"{marker} Weekly report is clear and useful for our support workflow.",
            "buy now click here free money http://spam.example http://bad.example",
        ]
    }
    result = assert_ok(await client.post("/feedback/bulk", json=payload), "feedbacklens bulk")
    if not result or result.get("created") != 2 or result.get("spam_rejected") != 1:
        raise E2EFailure(f"feedbacklens bulk: unexpected payload {result}")
    digest = assert_ok(await client.get("/digest"), "feedbacklens digest")
    if not digest:
        raise E2EFailure("feedbacklens digest: empty digest payload")
    return {"created": result["created"], "spam_rejected": result["spam_rejected"]}


async def run_worker_cron(client: httpx.AsyncClient, *, execute: bool) -> dict[str, Any]:
    secret = get_settings().cron_secret
    if not secret:
        raise E2EFailure("worker cron: CRON_SECRET missing")
    denied = await client.post("/worker/enqueue-periodic", headers={"Authorization": "Bearer wrong-secret"})
    if denied.status_code != 401:
        raise E2EFailure(f"worker cron guard: expected 401, got {denied.status_code}")
    result: dict[str, Any] = {"endpoint": "/worker/enqueue-periodic", "auth_guard": "401 on wrong secret"}
    if execute:
        payload = assert_ok(
            await client.post("/worker/enqueue-periodic", headers={"Authorization": f"Bearer {secret}"}),
            "worker enqueue-periodic",
        )
        if not payload or payload.get("status") != "success":
            raise E2EFailure(f"worker enqueue-periodic: unexpected payload {payload}")
        result["real_cron"] = payload
    return result


async def main(run_cron: bool = False) -> int:
    marker = f"codex-e2e-{int(time.time())}"
    user: User | None = None
    results: dict[str, Any] = {}
    try:
        user = await seed_user(marker)
        install_overrides(user)
        transport = httpx.ASGITransport(app=universal_main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            results["plans"] = verify_plan_catalog()
            results["filecleaner"] = await run_filecleaner(client)
            results["invoicefollow"] = await run_invoicefollow(client, marker)
            results["pricetrackr"] = await run_pricetrackr(client, marker)
            results["webhookmonitor"] = await run_webhookmonitor(client, marker)
            results["feedbacklens"] = await run_feedbacklens(client, marker)
            results["worker_cron"] = await run_worker_cron(client, execute=run_cron)

        print("REAL_BACKEND_E2E_OK")
        for key, value in results.items():
            print(f"{key}: {value}")
        return 0
    except Exception as exc:
        print(f"REAL_BACKEND_E2E_FAILED: {exc}")
        return 1
    finally:
        universal_main.app.dependency_overrides.clear()
        if user:
            await cleanup_marker(marker)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run real backend E2E checks against the configured database.")
    parser.add_argument("--run-cron", action="store_true", help="Execute the real /worker/enqueue-periodic cron endpoint.")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(run_cron=args.run_cron)))
