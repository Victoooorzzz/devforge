import base64
import hashlib
import hmac
import asyncio
import json
import sys
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

from fastapi.testclient import TestClient

import apps.webhookmonitor.backend.main as webhook_main
from backend_core.auth import User, get_current_user
from backend_core.database import get_session


def _trial_user(user_id=42):
    return User(
        id=user_id,
        email="owner@example.test",
        hashed_password="unused",
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=1),
    )


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
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.added = []
        self.committed = False

    async def execute(self, _query):
        if not self.responses:
            raise AssertionError("Unexpected database query")
        response = self.responses.pop(0)
        if isinstance(response, _FakeExecuteResult):
            return response
        return _FakeExecuteResult(rows=response)

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
        self.committed = True


def _client(session):
    webhook_main.app.dependency_overrides.clear()
    webhook_main.app.dependency_overrides[get_current_user] = lambda: _trial_user()

    async def override_session():
        yield session

    webhook_main.app.dependency_overrides[get_session] = override_session
    return TestClient(webhook_main.app)


def _request(request_id=7, **overrides):
    payload = {
        "id": request_id,
        "endpoint_id": 99,
        "user_id": 42,
        "method": "POST",
        "path": "/in/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "headers_json": '{"content-type":"application/json","stripe-signature":"t=1,v1=sig"}',
        "body": '{"type":"payment_intent.succeeded","data":{"object":{"amount":9900}}}',
        "query_params_json": '{"mode":"live"}',
        "ip_address": "203.0.113.10",
        "received_at": datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc),
        "retry_count": 0,
        "next_retry_at": None,
        "last_retry_status": 500,
        "auto_retry_enabled": False,
        "forward_error": "upstream timeout",
        "signature_valid": True,
        "signature_error": "",
        "signature_provider": "stripe",
        "replay_of_request_id": None,
        "replay_target_url": "",
        "replay_status": "",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


class WebhookSignatureSpecTests(unittest.TestCase):
    def test_signature_validation_supports_required_providers(self):
        body = b'{"type":"invoice.paid"}'
        secret = "whsec_test"
        timestamp = int(datetime.now(timezone.utc).timestamp())

        stripe_sig = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
        github_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        shopify_sig = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
        generic_sha1 = hmac.new(secret.encode(), body, hashlib.sha1).hexdigest()

        self.assertTrue(webhook_main.validate_webhook_signature(
            "stripe",
            secret,
            {"stripe-signature": f"t={timestamp},v1={stripe_sig}"},
            body,
        )["valid"])
        self.assertTrue(webhook_main.validate_webhook_signature(
            "github",
            secret,
            {"x-hub-signature-256": f"sha256={github_sig}"},
            body,
        )["valid"])
        self.assertTrue(webhook_main.validate_webhook_signature(
            "shopify",
            secret,
            {"x-shopify-hmac-sha256": shopify_sig},
            body,
        )["valid"])
        self.assertTrue(webhook_main.validate_webhook_signature(
            "generic",
            secret,
            {"x-signature": f"sha1={generic_sha1}"},
            body,
        )["valid"])

    def test_stripe_signature_reports_timestamp_failures(self):
        body = b'{"type":"invoice.paid"}'
        secret = "whsec_test"
        old_timestamp = int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp())
        signature = hmac.new(secret.encode(), f"{old_timestamp}.".encode() + body, hashlib.sha256).hexdigest()

        result = webhook_main.validate_webhook_signature(
            "stripe",
            secret,
            {"stripe-signature": f"t={old_timestamp},v1={signature}"},
            body,
        )

        self.assertFalse(result["valid"])
        self.assertEqual(result["error"], "timestamp_too_old")
        self.assertIn("diff_minutes", result["details"])


class WebhookEndpointAndMetadataSpecTests(unittest.TestCase):
    def tearDown(self):
        webhook_main.app.dependency_overrides.clear()

    def test_config_creates_public_in_uuid_endpoint(self):
        session = _FakeSession([[]])
        response = _client(session).get("/webhooks/config")

        self.assertEqual(response.status_code, 200)
        endpoint_url = response.json()["endpoint_url"]
        parsed = urlparse(endpoint_url)
        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}", webhook_main.WEBHOOK_PUBLIC_BASE_URL)
        self.assertTrue(parsed.path.startswith("/in/"))
        generated_uuid = parsed.path.rsplit("/", 1)[-1]
        self.assertEqual(str(webhook_main.uuid.UUID(generated_uuid, version=4)), generated_uuid)
        self.assertEqual(session.added[0].slug, generated_uuid)

    def test_persist_records_query_ip_signature_and_alert_metadata(self):
        managed_session = _FakeSession([[], []])
        signature_result = {
            "valid": False,
            "error": "signature_mismatch",
            "provider": "stripe",
            "details": {"header": "stripe-signature"},
        }

        @asynccontextmanager
        async def fake_managed_session():
            yield managed_session

        with patch.object(webhook_main, "get_managed_session", fake_managed_session):
            asyncio.run(
                webhook_main._persist_and_forward(
                    endpoint_id=99,
                    user_id=42,
                    method="POST",
                    path="/in/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                    headers={"stripe-signature": "bad"},
                    body='{"type":"invoice.paid"}',
                    query_params={"mode": "test"},
                    ip_address="203.0.113.10",
                    signature_result=signature_result,
                )
            )

        persisted = next(item for item in managed_session.added if isinstance(item, webhook_main.WebhookRequest))
        self.assertEqual(json.loads(persisted.query_params_json), {"mode": "test"})
        self.assertEqual(persisted.ip_address, "203.0.113.10")
        self.assertFalse(persisted.signature_valid)
        self.assertEqual(persisted.signature_error, "signature_mismatch")
        self.assertEqual(persisted.signature_provider, "stripe")

    def test_public_in_route_accepts_ten_megabyte_limit_contract(self):
        self.assertEqual(webhook_main.MAX_WEBHOOK_BODY_BYTES, 10 * 1024 * 1024)


class WebhookReplaySearchSpecTests(unittest.TestCase):
    def tearDown(self):
        webhook_main.app.dependency_overrides.clear()

    def test_replay_event_sends_to_alternate_url_and_records_new_event(self):
        original = _request(7)
        session = _FakeSession([
            [original],
        ])
        calls = []

        class FakeAsyncClient:
            def __init__(self, timeout=None):
                self.timeout = timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def request(self, **kwargs):
                calls.append(kwargs)
                return SimpleNamespace(status_code=204, text="")

        with patch.object(webhook_main.httpx, "AsyncClient", FakeAsyncClient):
            response = _client(session).post(
                "/webhooks/events/7/replay",
                json={
                    "mode": "alternate",
                    "target_url": "https://example.com/webhook",
                    "body_override": '{"type":"payment_intent.succeeded","data":{"object":{"amount":10000}}}',
                    "headers_override": {"x-debug": "true"},
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(calls[0]["url"], "https://example.com/webhook")
        self.assertEqual(calls[0]["method"], "POST")
        self.assertEqual(calls[0]["content"], b'{"type":"payment_intent.succeeded","data":{"object":{"amount":10000}}}')
        replay = next(item for item in session.added if isinstance(item, webhook_main.WebhookRequest))
        self.assertEqual(replay.replay_of_request_id, 7)
        self.assertEqual(replay.replay_target_url, "https://example.com/webhook")
        self.assertEqual(replay.replay_status, "success")

    def test_search_filters_json_path_status_method_provider_and_date(self):
        matching = _request(8, last_retry_status=202, signature_provider="stripe")
        wrong_method = _request(9, method="PATCH", last_retry_status=202, signature_provider="stripe")
        wrong_provider = _request(10, last_retry_status=202, signature_provider="github")
        session = _FakeSession([
            [matching, wrong_method, wrong_provider],
        ])

        response = _client(session).post(
            "/webhooks/search",
            json={
                "json_path": "type",
                "equals": "payment_intent.succeeded",
                "status": "successful",
                "method": "POST",
                "provider": "stripe",
                "date_from": "2026-06-20T00:00:00+00:00",
                "date_to": "2026-06-21T00:00:00+00:00",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["id"], 8)


if __name__ == "__main__":
    unittest.main()
