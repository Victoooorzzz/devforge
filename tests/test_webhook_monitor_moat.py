import sys
import unittest
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


class _FakeExecuteResult:
    def __init__(self, rows=None):
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class _FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)

    async def execute(self, _query):
        if not self.responses:
            raise AssertionError("Unexpected database query")
        response = self.responses.pop(0)
        if isinstance(response, _FakeExecuteResult):
            return response
        return _FakeExecuteResult(response)


def _trial_user():
    return User(
        id=42,
        email="owner@example.test",
        hashed_password="unused",
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=1),
    )


def _request(request_id, *, body, headers=None):
    return SimpleNamespace(
        id=request_id,
        endpoint_id=7,
        user_id=42,
        method="POST",
        path="/hook/test",
        headers_json=headers or "{}",
        body=body,
        received_at=datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc),
        retry_count=0,
        next_retry_at=None,
        last_retry_status=None,
        auto_retry_enabled=False,
    )


class WebhookMonitorMoatTests(unittest.TestCase):
    def tearDown(self):
        webhook_main.app.dependency_overrides.clear()

    def _client(self, responses):
        webhook_main.app.dependency_overrides.clear()
        webhook_main.app.dependency_overrides[get_current_user] = _trial_user

        async def override_session():
            yield _FakeSession(responses)

        webhook_main.app.dependency_overrides[get_session] = override_session
        return TestClient(webhook_main.app)

    def test_request_diff_reports_added_removed_changed_fields_with_redaction(self):
        base_request = _request(
            1,
            body='{"type":"invoice.created","data":{"amount":9,"token":"old-secret"}}',
            headers='{"authorization":"Bearer old","x-stripe-version":"2024-01-01"}',
        )
        new_request = _request(
            2,
            body='{"type":"invoice.paid","data":{"plan":"pro","token":"new-secret"}}',
            headers='{"authorization":"Bearer new","x-stripe-version":"2025-01-01"}',
        )

        response = self._client([
            [new_request],
            [base_request],
        ]).get("/webhooks/requests/2/diff?base_request_id=1")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["request_id"], 2)
        self.assertEqual(payload["base_request_id"], 1)
        self.assertIn(
            {"path": "$.type", "old_value": "invoice.created", "new_value": "invoice.paid"},
            payload["body"]["changed"],
        )
        self.assertIn({"path": "$.data.plan", "value": "pro"}, payload["body"]["added"])
        self.assertIn({"path": "$.data.amount", "old_value": 9}, payload["body"]["removed"])
        self.assertIn(
            {"path": "$.data.token", "old_value": "[redacted]", "new_value": "[redacted]"},
            payload["body"]["changed"],
        )
        self.assertIn(
            {"path": "$.authorization", "old_value": "[redacted]", "new_value": "[redacted]"},
            payload["headers"]["changed"],
        )

    def test_request_schema_validation_returns_actionable_errors(self):
        request = _request(
            2,
            body='{"type":"invoice.paid","data":{"plan":"pro"},"unexpected":true}',
        )
        schema = {
            "type": "object",
            "required": ["type", "data"],
            "additionalProperties": False,
            "properties": {
                "type": {"const": "invoice.paid"},
                "data": {
                    "type": "object",
                    "required": ["amount"],
                    "properties": {"amount": {"type": "number"}},
                },
            },
        }

        response = self._client([
            [request],
        ]).post("/webhooks/requests/2/validate-schema", json={"schema": schema})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["request_id"], 2)
        messages = [error["message"] for error in payload["errors"]]
        self.assertTrue(any("amount" in message for message in messages))
        self.assertTrue(any("unexpected" in message for message in messages))

    def test_request_export_returns_executable_curl_for_owned_event(self):
        request = _request(
            2,
            body='{"type":"invoice.paid","data":{"amount":9900}}',
            headers='{"content-type":"application/json","stripe-signature":"t=1,v1=sig","host":"testserver"}',
        )

        response = self._client([
            [request],
        ]).get("/webhooks/requests/2/export?format=curl")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"].split(";")[0], "text/plain")
        self.assertIn("webhook-request-2.curl.sh", response.headers["content-disposition"])
        script = response.text
        self.assertIn("curl --request POST", script)
        self.assertIn("'https://webhookmonitor.devforgeapp.pro/hook/test'", script)
        self.assertIn("--header 'content-type: application/json'", script)
        self.assertIn("--header 'stripe-signature: t=1,v1=sig'", script)
        self.assertNotIn("--header 'host:", script.lower())
        self.assertIn("--data-raw '{\"type\":\"invoice.paid\",\"data\":{\"amount\":9900}}'", script)

    def test_request_export_returns_postman_collection_for_owned_event(self):
        request = _request(
            2,
            body='{"type":"invoice.paid","data":{"amount":9900}}',
            headers='{"content-type":"application/json","stripe-signature":"t=1,v1=sig"}',
        )

        response = self._client([
            [request],
        ]).get("/webhooks/requests/2/export?format=postman")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"].split(";")[0], "application/json")
        self.assertIn("webhook-request-2.postman_collection.json", response.headers["content-disposition"])
        collection = response.json()
        self.assertEqual(
            collection["info"]["schema"],
            "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        )
        exported_request = collection["item"][0]["request"]
        self.assertEqual(exported_request["method"], "POST")
        self.assertEqual(exported_request["url"]["raw"], "https://webhookmonitor.devforgeapp.pro/hook/test")
        self.assertIn({"key": "stripe-signature", "value": "t=1,v1=sig"}, exported_request["header"])
        self.assertEqual(exported_request["body"]["mode"], "raw")
        self.assertEqual(exported_request["body"]["raw"], '{"type":"invoice.paid","data":{"amount":9900}}')

    def test_failed_log_status_includes_timeout_forward_errors(self):
        timeout_request = SimpleNamespace(last_retry_status=None, forward_error="Request timed out", auto_retry_enabled=False)

        self.assertTrue(webhook_main._matches_log_status(timeout_request, "failed"))

    def test_forward_errors_are_sanitized_before_storage(self):
        message = 'Forward failed: {"token":"sk_live_secret","authorization":"Bearer abc"}'

        sanitized = webhook_main._safe_forward_error(message)

        self.assertNotIn("sk_live_secret", sanitized)
        self.assertNotIn("Bearer abc", sanitized)
        self.assertIn("[redacted]", sanitized)


if __name__ == "__main__":
    unittest.main()
