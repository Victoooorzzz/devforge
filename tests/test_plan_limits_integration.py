import asyncio
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

from fastapi.testclient import TestClient

import apps.pricetrackr.backend.main as tracker_main
import apps.webhookmonitor.backend.main as webhook_main
from backend_core.plan_limits import resolve_user_plan
from backend_core.auth import ProfileResponse, User, get_current_user
from backend_core.database import get_session


TRIAL_PRICE_TRACKERS = 5
TRIAL_WEBHOOKS_PER_DAY = 100
LEGACY_WEBHOOKS_PER_MINUTE = 60


class _FakeExecuteResult:
    def __init__(self, rows=None, scalar=None):
        self.rows = rows or []
        self.scalar = scalar

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None

    def scalar_one(self):
        return self.scalar


class _QueryAwareSession:
    def __init__(
        self,
        *,
        user=None,
        endpoint=None,
        active_tracker_count=0,
        recent_webhook_count=0,
        product_access_rows=None,
    ):
        self.user = user
        self.endpoint = endpoint
        self.active_tracker_count = active_tracker_count
        self.recent_webhook_count = recent_webhook_count
        self.product_access_rows = product_access_rows or []
        self.added = []
        self.queries = []

    async def execute(self, query):
        query_text = str(query)
        self.queries.append(query_text)

        if "count(tracked_urls.id)" in query_text:
            return _FakeExecuteResult(scalar=self.active_tracker_count)
        if "count(webhook_requests.id)" in query_text:
            return _FakeExecuteResult(scalar=self.recent_webhook_count)
        if "FROM webhook_endpoints" in query_text:
            return _FakeExecuteResult(rows=[self.endpoint] if self.endpoint else [])
        if "FROM webhook_settings" in query_text:
            return _FakeExecuteResult(rows=[])
        if "FROM users" in query_text:
            return _FakeExecuteResult(rows=[self.user] if self.user else [])
        if "FROM user_product_access" in query_text:
            return _FakeExecuteResult(rows=self.product_access_rows)
        raise AssertionError(f"Unexpected query: {query_text}")

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        for index, item in enumerate(self.added, start=1):
            if getattr(item, "id", None) is None:
                item.id = index

    async def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = len(self.added) or 1

    async def commit(self):
        return None

    async def delete(self, _item):
        return None


def _trial_user(user_id=42):
    return User(
        id=user_id,
        email="owner@example.test",
        hashed_password="unused",
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=1),
    )


def _paid_user(user_id=42):
    return User(
        id=user_id,
        email="owner@example.test",
        hashed_password="unused",
        is_active=True,
        trial_ends_at=None,
    )


class PlanLimitsIntegrationTests(unittest.TestCase):
    def tearDown(self):
        tracker_main.app.dependency_overrides.clear()
        webhook_main.app.dependency_overrides.clear()

    def _post_tracker(self, *, user, session, check_frequency_hours=24):
        tracker_main.app.dependency_overrides.clear()
        tracker_main.app.dependency_overrides[get_current_user] = lambda: user

        async def override_session():
            yield session

        tracker_main.app.dependency_overrides[get_session] = override_session

        original_fetch_price = tracker_main.scraper.fetch_price
        original_fetch_stock = tracker_main.scraper.fetch_stock
        calls = {"price": 0, "stock": 0}

        async def fake_fetch_price(_url):
            calls["price"] += 1
            return 19.99

        async def fake_fetch_stock(_url):
            calls["stock"] += 1
            return True

        tracker_main.scraper.fetch_price = fake_fetch_price
        tracker_main.scraper.fetch_stock = fake_fetch_stock
        try:
            response = TestClient(tracker_main.app).post(
                "/trackers",
                json={
                    "url": "https://example.com/product",
                    "label": "Example product",
                    "check_frequency_hours": check_frequency_hours,
                },
            )
        finally:
            tracker_main.scraper.fetch_price = original_fetch_price
            tracker_main.scraper.fetch_stock = original_fetch_stock
            tracker_main.app.dependency_overrides.clear()
        return response, calls

    def test_pricetrackr_free_rejects_hourly_check_frequency(self):
        response, calls = self._post_tracker(
            user=_trial_user(),
            session=_QueryAwareSession(),
            check_frequency_hours=1,
        )

        self.assertEqual(response.status_code, 429)
        self.assertIn("Free plan", response.json()["detail"])
        self.assertEqual(calls, {"price": 0, "stock": 0})

    def test_pricetrackr_trial_rejects_tracker_count_over_limit(self):
        session = _QueryAwareSession(active_tracker_count=TRIAL_PRICE_TRACKERS)
        response, calls = self._post_tracker(user=_trial_user(), session=session)

        self.assertEqual(response.status_code, 429)
        self.assertIn("5 active trackers", response.json()["detail"])
        self.assertEqual(calls, {"price": 0, "stock": 0})

    def test_webhookmonitor_free_rejects_ingest_above_daily_limit(self):
        endpoint = SimpleNamespace(id=10, user_id=77, slug="trial-slug")
        session = _QueryAwareSession(
            user=_trial_user(77),
            endpoint=endpoint,
            recent_webhook_count=TRIAL_WEBHOOKS_PER_DAY,
        )

        async def override_session():
            yield session

        webhook_main.app.dependency_overrides[get_session] = override_session

        response = TestClient(webhook_main.app).post("/in/trial-slug", json={"ok": True})

        self.assertEqual(response.status_code, 429)
        self.assertIn("Free plan", response.json()["detail"])
        self.assertIn("100 events per day", response.json()["detail"])

    def test_webhookmonitor_paid_allows_above_legacy_sixty_per_minute(self):
        endpoint = SimpleNamespace(id=10, user_id=77, slug="paid-slug")
        session = _QueryAwareSession(
            user=_paid_user(77),
            endpoint=endpoint,
            recent_webhook_count=LEGACY_WEBHOOKS_PER_MINUTE,
            product_access_rows=[SimpleNamespace(user_id=77, app_name="webhookmonitor", is_active=True)],
        )
        persisted = []

        async def override_session():
            yield session

        async def fake_persist_and_forward(**kwargs):
            persisted.append(kwargs)

        original_persist = webhook_main._persist_and_forward
        webhook_main._persist_and_forward = fake_persist_and_forward
        webhook_main.app.dependency_overrides[get_session] = override_session
        try:
            response = TestClient(webhook_main.app).post("/in/paid-slug", json={"ok": True})
        finally:
            webhook_main._persist_and_forward = original_persist
            webhook_main.app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "received")
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["user_id"], 77)
        self.assertEqual(persisted[0]["query_params"], {})
        self.assertTrue(persisted[0]["ip_address"])

    def test_legacy_active_user_without_product_access_resolves_to_pro(self):
        session = _QueryAwareSession(user=_paid_user(77), product_access_rows=[])

        plan = asyncio.run(resolve_user_plan(_paid_user(77), session, "feedbacklens"))

        self.assertEqual(plan, "pro")

    def test_profile_response_exposes_product_plans_for_dashboards(self):
        fields = ProfileResponse.model_fields

        self.assertIn("plans_by_product", fields)


if __name__ == "__main__":
    unittest.main()
