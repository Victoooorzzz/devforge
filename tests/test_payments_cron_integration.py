import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

from fastapi.testclient import TestClient

import apps.feedbacklens.backend.main as feedback_main
import apps.invoicefollow.backend.main as invoice_main
import apps.pricetrackr.backend.main as tracker_main
import apps.webhookmonitor.backend.main as webhook_main
import backend_core.universal_main as universal_main
from apps.filecleaner.backend.main import app as file_app
from backend_core.auth import User, get_current_user
from backend_core.config import get_settings
from backend_core.database import get_session
from backend_core.product_access import UserProductAccess
import backend_core.polar_handler as polar_handler


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


class _FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.added = []
        self.flushed = False

    async def execute(self, _query):
        if not self.responses:
            raise AssertionError("Unexpected database query")
        response = self.responses.pop(0)
        if isinstance(response, _FakeExecuteResult):
            return response
        return _FakeExecuteResult(response)

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flushed = True


class _FakePolarResponse:
    status_code = 201
    text = "created"

    def json(self):
        return {"url": "https://polar.example.test/checkout/session_123"}


class _FakePolarAsyncClient:
    requests = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, headers=None):
        self.requests.append({"url": url, "json": json, "headers": headers})
        return _FakePolarResponse()


def _trial_user():
    return User(
        id=42,
        email="owner@example.test",
        hashed_password="unused",
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=1),
    )


class PaymentIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.original_async_client = polar_handler.httpx.AsyncClient
        self.original_settings = {
            "debug": polar_handler.settings.debug,
            "polar_server": polar_handler.settings.polar_server,
            "polar_api_url": polar_handler.settings.polar_api_url,
            "polar_access_token": polar_handler.settings.polar_access_token,
            "polar_webhook_secret": polar_handler.settings.polar_webhook_secret,
            "polar_product_id_filecleaner": polar_handler.settings.polar_product_id_filecleaner,
            "polar_product_id_filecleaner_team": polar_handler.settings.polar_product_id_filecleaner_team,
            "allowed_origins": polar_handler.settings.allowed_origins,
            "frontend_url": polar_handler.settings.frontend_url,
        }
        _FakePolarAsyncClient.requests = []
        polar_handler.httpx.AsyncClient = _FakePolarAsyncClient
        polar_handler.settings.polar_server = "sandbox"
        polar_handler.settings.polar_api_url = ""
        polar_handler.settings.polar_access_token = "polar_test_token"
        polar_handler.settings.polar_webhook_secret = ""
        polar_handler.settings.debug = True
        polar_handler.settings.polar_product_id_filecleaner = "prod_filecleaner"
        polar_handler.settings.polar_product_id_filecleaner_team = "prod_filecleaner_team"
        polar_handler.settings.allowed_origins = "https://filecleaner.devforgeapp.pro"
        polar_handler.settings.frontend_url = "https://fallback.devforgeapp.pro"

    def tearDown(self):
        polar_handler.httpx.AsyncClient = self.original_async_client
        for key, value in self.original_settings.items():
            setattr(polar_handler.settings, key, value)
        file_app.dependency_overrides.clear()

    def test_polar_checkout_uses_app_product_and_allowed_origin(self):
        file_app.dependency_overrides[get_current_user] = _trial_user

        response = TestClient(file_app).post(
            "/polar/checkout",
            headers={"origin": "https://filecleaner.devforgeapp.pro"},
            json={"app_name": "filecleaner"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["checkout_url"],
            "https://polar.example.test/checkout/session_123",
        )
        self.assertEqual(len(_FakePolarAsyncClient.requests), 1)
        request = _FakePolarAsyncClient.requests[0]
        self.assertEqual(request["url"], "https://sandbox-api.polar.sh/v1/checkouts/")
        self.assertEqual(request["headers"]["Authorization"], "Bearer polar_test_token")
        self.assertEqual(request["json"]["product_id"], "prod_filecleaner")
        self.assertEqual(request["json"]["external_customer_id"], "42")
        self.assertEqual(
            request["json"]["success_url"],
            "https://filecleaner.devforgeapp.pro/dashboard?checkout_id={CHECKOUT_ID}",
        )

    def test_polar_checkout_uses_team_product_when_plan_is_team(self):
        file_app.dependency_overrides[get_current_user] = _trial_user

        response = TestClient(file_app).post(
            "/polar/checkout",
            headers={"origin": "https://filecleaner.devforgeapp.pro"},
            json={"app_name": "filecleaner", "plan": "team"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(_FakePolarAsyncClient.requests), 1)
        self.assertEqual(_FakePolarAsyncClient.requests[0]["json"]["product_id"], "prod_filecleaner_team")

    def test_polar_webhook_activates_product_access(self):
        user = User(
            id=42,
            email="owner@example.test",
            hashed_password="unused",
            trial_ends_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        session = _FakeSession([
            [user],
            [],
            _FakeExecuteResult(scalar=0),
        ])

        async def override_session():
            yield session

        file_app.dependency_overrides[get_session] = override_session

        payload = {
            "type": "subscription.active",
            "data": {
                "customer": {"external_id": "42"},
                "product_id": "prod_filecleaner",
            },
        }
        response = TestClient(file_app).post(
            "/webhooks/polar",
            content=json.dumps(payload),
            headers={"content-type": "application/json"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        access_rows = [item for item in session.added if isinstance(item, UserProductAccess)]
        self.assertEqual(len(access_rows), 1)
        self.assertEqual(access_rows[0].app_name, "filecleaner")
        self.assertEqual(access_rows[0].polar_product_id, "prod_filecleaner")
        self.assertTrue(access_rows[0].is_active)
        self.assertTrue(user.is_active)
        self.assertIsNone(user.trial_ends_at)
        self.assertTrue(session.flushed)


class CronIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.original_cron_secret = os.environ.get("CRON_SECRET")
        os.environ["CRON_SECRET"] = "cron-test-secret"
        get_settings.cache_clear()

    def tearDown(self):
        if self.original_cron_secret is None:
            os.environ.pop("CRON_SECRET", None)
        else:
            os.environ["CRON_SECRET"] = self.original_cron_secret
        get_settings.cache_clear()

    def test_universal_cron_requires_secret(self):
        response = TestClient(universal_main.app).post(
            "/worker/enqueue-periodic",
            headers={"Authorization": "Bearer wrong"},
        )

        self.assertEqual(response.status_code, 401)

    def test_universal_cron_runs_all_product_jobs_in_isolation(self):
        calls = []
        originals = {
            "run_price_updates": universal_main.run_price_updates,
            "enqueue_overdue_reminders": universal_main.enqueue_overdue_reminders,
            "poll_feedback_sources": universal_main.poll_feedback_sources,
            "weekly_summary_cron": universal_main.weekly_summary_cron,
            "check_webhook_silences": universal_main.check_webhook_silences,
            "cleanup_old_logs": universal_main.cleanup_old_logs,
            "cron_cleanup_files": universal_main.cron_cleanup_files,
            "run_worker_cycle": universal_main.run_worker_cycle,
        }

        async def fake_job(name, result=None):
            calls.append(name)
            return result

        universal_main.run_price_updates = lambda: fake_job("pricetrackr")
        universal_main.enqueue_overdue_reminders = lambda: fake_job("invoicefollow")
        universal_main.poll_feedback_sources = lambda: fake_job("feedbacklens_poll", {"status": "success"})
        universal_main.weekly_summary_cron = lambda: fake_job("feedbacklens_digest")
        universal_main.check_webhook_silences = lambda: fake_job("webhookmonitor_silence")
        universal_main.cleanup_old_logs = lambda: fake_job("webhookmonitor_cleanup")
        universal_main.cron_cleanup_files = lambda: fake_job("filecleaner", 3)
        universal_main.run_worker_cycle = lambda: fake_job("worker", 7)

        try:
            response = TestClient(universal_main.app).post(
                "/worker/enqueue-periodic",
                headers={"Authorization": "Bearer cron-test-secret"},
            )
        finally:
            for name, original in originals.items():
                setattr(universal_main, name, original)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            calls,
            [
                "pricetrackr",
                "invoicefollow",
                "feedbacklens_poll",
                "feedbacklens_digest",
                "webhookmonitor_silence",
                "webhookmonitor_cleanup",
                "filecleaner",
                "worker",
            ],
        )
        payload = response.json()
        self.assertEqual(payload["results"]["filecleaner"], "cleaned 3 files")
        self.assertEqual(payload["processed_jobs"], 7)

    def test_product_cron_endpoints_accept_cron_secret_without_user_login(self):
        calls = []
        originals = {
            "tracker": tracker_main.run_price_updates,
            "invoice": invoice_main.enqueue_overdue_reminders,
            "feedback": feedback_main.weekly_summary_cron,
            "webhook_silence": webhook_main.check_webhook_silences,
            "webhook_cleanup": webhook_main.cleanup_old_logs,
        }

        async def fake_job(name, result=None):
            calls.append(name)
            return result

        tracker_main.run_price_updates = lambda: fake_job("tracker")
        invoice_main.enqueue_overdue_reminders = lambda: fake_job("invoice")
        feedback_main.weekly_summary_cron = lambda: fake_job("feedback")
        webhook_main.check_webhook_silences = lambda: fake_job("webhook_silence")
        webhook_main.cleanup_old_logs = lambda: fake_job("webhook_cleanup", 2)

        try:
            requests = [
                (tracker_main.app, "/trackers/cron/update"),
                (invoice_main.app, "/invoices/cron/reminders/enqueue"),
                (feedback_main.app, "/feedback/cron/summary"),
                (webhook_main.app, "/webhooks/cron/silence"),
                (webhook_main.app, "/webhooks/cron/cleanup"),
            ]
            responses = [
                TestClient(app).post(path, headers={"Authorization": "Bearer cron-test-secret"})
                for app, path in requests
            ]
        finally:
            tracker_main.run_price_updates = originals["tracker"]
            invoice_main.enqueue_overdue_reminders = originals["invoice"]
            feedback_main.weekly_summary_cron = originals["feedback"]
            webhook_main.check_webhook_silences = originals["webhook_silence"]
            webhook_main.cleanup_old_logs = originals["webhook_cleanup"]

        self.assertEqual([response.status_code for response in responses], [200, 200, 200, 200, 200])
        self.assertEqual(calls, ["tracker", "invoice", "feedback", "webhook_silence", "webhook_cleanup"])
        self.assertEqual(responses[-1].json()["deleted_count"], 2)


if __name__ == "__main__":
    unittest.main()
