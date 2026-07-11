import sys
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

from fastapi.testclient import TestClient

import apps.webhookmonitor.backend.main as webhook_main
from backend_core.auth import User, get_current_user
from backend_core.database import get_session
from backend_core.outbox_models import SystemOutbox


class _FakeExecuteResult:
    def __init__(self, rows=None):
        self.rows = rows or []

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class _RouteSession:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.added = []
        self.flushed = False
        self.deleted = []

    async def execute(self, query):
        query_text = str(query).lower()
        if query_text.startswith("delete"):
            self.deleted.append(query)
            return _FakeExecuteResult([])
        if not self.responses:
            return _FakeExecuteResult([])
        response = self.responses.pop(0)
        if isinstance(response, _FakeExecuteResult):
            return response
        return _FakeExecuteResult(response)

    def add(self, item):
        self.added.append(item)
        if getattr(item, "id", None) is None:
            item.id = len(self.added)

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.flushed = True


class _ManagedSession(_RouteSession):
    async def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = len(self.added)


def _trial_user():
    return User(
        id=42,
        email="owner@example.test",
        hashed_password="unused",
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=1),
    )


class WebhookConditionalForwardingTests(unittest.TestCase):
    def tearDown(self):
        webhook_main.app.dependency_overrides.clear()

    def _client(self, session):
        webhook_main.app.dependency_overrides.clear()
        webhook_main.app.dependency_overrides[get_current_user] = _trial_user

        async def override_session():
            yield session

        webhook_main.app.dependency_overrides[get_session] = override_session
        return TestClient(webhook_main.app)

    def test_forward_rule_api_creates_and_lists_public_conditional_destinations(self):
        create_session = _RouteSession()
        response = self._client(create_session).post(
            "/webhooks/forward-rules",
            json={
                "name": "Stripe paid",
                "match_path": "event",
                "match_equals": "invoice.paid",
                "forward_url": "https://example.com/primary-webhook",
                "fallback_url": "https://example.com/fallback-webhook",
                "auto_retry_enabled": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Stripe paid")
        self.assertEqual(response.json()["match_path"], "event")
        self.assertEqual(response.json()["forward_url"], "https://example.com/primary-webhook")
        self.assertEqual(response.json()["fallback_url"], "https://example.com/fallback-webhook")
        self.assertTrue(response.json()["auto_retry_enabled"])
        self.assertTrue(create_session.flushed)

        saved_rule = create_session.added[-1]
        list_response = self._client(_RouteSession([[saved_rule]])).get("/webhooks/forward-rules")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()[0]["name"], "Stripe paid")

    def test_forward_rule_api_rejects_private_fallback_destinations(self):
        response = self._client(_RouteSession()).post(
            "/webhooks/forward-rules",
            json={
                "name": "Unsafe",
                "match_path": "event",
                "match_equals": "invoice.paid",
                "forward_url": "https://example.com/primary-webhook",
                "fallback_url": "http://127.0.0.1:8000/private",
                "auto_retry_enabled": False,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("public http(s) URL", response.json()["detail"])

    def test_matching_forward_rule_queues_destination_fallback_and_retry(self):
        rule = webhook_main.WebhookForwardRule(
            id=9,
            user_id=42,
            name="Stripe paid",
            match_path="event",
            match_equals="invoice.paid",
            forward_url="https://example.com/primary-webhook",
            fallback_url="https://example.com/fallback-webhook",
            auto_retry_enabled=True,
            is_active=True,
        )
        request = webhook_main.WebhookRequest(
            id=1,
            endpoint_id=7,
            user_id=42,
            method="POST",
            path="/hook/test",
            body='{"event":"invoice.paid","data":{"amount":99}}',
        )
        session = _ManagedSession([[request], [], [rule]])
        original_get_managed_session = webhook_main.get_managed_session

        @asynccontextmanager
        async def fake_managed_session():
            yield session

        webhook_main.get_managed_session = fake_managed_session
        try:
            import asyncio

            asyncio.run(
                webhook_main._persist_and_forward(
                    request_id=1,
                    endpoint_id=7,
                    user_id=42,
                    method="POST",
                    path="/hook/test",
                    headers={"content-type": "application/json"},
                    body='{"event":"invoice.paid","data":{"amount":99}}',
                )
            )
        finally:
            webhook_main.get_managed_session = original_get_managed_session

        queued_jobs = [item for item in session.added if isinstance(item, SystemOutbox)]
        self.assertEqual(len(queued_jobs), 1)
        job = queued_jobs[0]
        self.assertEqual(job.max_attempts, 3)
        self.assertEqual(job.payload["request_id"], 1)
        self.assertEqual(job.payload["forward_rule_id"], 9)
        self.assertEqual(job.payload["forward_url"], "https://example.com/primary-webhook")
        self.assertEqual(job.payload["fallback_url"], "https://example.com/fallback-webhook")

        saved_requests = [item for item in session.added if isinstance(item, webhook_main.WebhookRequest)]
        self.assertTrue(saved_requests[0].auto_retry_enabled)

    def test_worker_uses_fallback_url_when_primary_forward_fails(self):
        request = webhook_main.WebhookRequest(
            id=5,
            endpoint_id=7,
            user_id=42,
            method="POST",
            path="/hook/test",
            headers_json='{"content-type":"application/json"}',
            body='{"event":"invoice.paid"}',
        )
        session = _ManagedSession([[request]])
        original_get_managed_session = webhook_main.get_managed_session
        original_async_client = webhook_main.httpx.AsyncClient

        class _FakeResponse:
            def __init__(self, status_code):
                self.status_code = status_code

        class _FakeAsyncClient:
            calls = []

            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def request(self, **kwargs):
                self.calls.append(kwargs)
                return _FakeResponse(500 if len(self.calls) == 1 else 204)

        @asynccontextmanager
        async def fake_managed_session():
            yield session

        webhook_main.get_managed_session = fake_managed_session
        webhook_main.httpx.AsyncClient = _FakeAsyncClient
        try:
            import asyncio

            result = asyncio.run(
                webhook_main.process_webhook_forward(
                    {
                        "request_id": 5,
                        "forward_url": "https://example.com/primary-webhook",
                        "fallback_url": "https://example.com/fallback-webhook",
                    }
                )
            )
        finally:
            webhook_main.get_managed_session = original_get_managed_session
            webhook_main.httpx.AsyncClient = original_async_client

        self.assertEqual([call["url"] for call in _FakeAsyncClient.calls], [
            "https://example.com/primary-webhook",
            "https://example.com/fallback-webhook",
        ])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["forward_url"], "https://example.com/fallback-webhook")
        self.assertEqual(request.last_retry_status, 204)

    def test_worker_persists_retry_when_primary_and_fallback_network_fail(self):
        request = webhook_main.WebhookRequest(
            id=6,
            endpoint_id=7,
            user_id=42,
            method="POST",
            path="/hook/test",
            headers_json='{"content-type":"application/json"}',
            body='{"event":"invoice.failed"}',
        )
        session = _ManagedSession([[request]])
        original_get_managed_session = webhook_main.get_managed_session
        original_async_client = webhook_main.httpx.AsyncClient

        class _FailingAsyncClient:
            calls = []

            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def request(self, **kwargs):
                self.calls.append(kwargs)
                raise webhook_main.httpx.RequestError("offline")

        @asynccontextmanager
        async def fake_managed_session():
            yield session

        webhook_main.get_managed_session = fake_managed_session
        webhook_main.httpx.AsyncClient = _FailingAsyncClient
        try:
            import asyncio

            result = asyncio.run(
                webhook_main.process_webhook_forward(
                    {
                        "request_id": 6,
                        "forward_url": "https://example.com/primary-webhook",
                        "fallback_url": "https://example.com/fallback-webhook",
                    }
                )
            )
        finally:
            webhook_main.get_managed_session = original_get_managed_session
            webhook_main.httpx.AsyncClient = original_async_client

        self.assertEqual([call["url"] for call in _FailingAsyncClient.calls], [
            "https://example.com/primary-webhook",
            "https://example.com/fallback-webhook",
        ])
        self.assertEqual(request.retry_count, 1)
        self.assertTrue(session.flushed)
        self.assertEqual(result["status"], "failed")
        self.assertIn("fallback", result["reason"])


if __name__ == "__main__":
    unittest.main()
