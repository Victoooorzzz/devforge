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


TEST_ENCRYPTION_KEY = base64.urlsafe_b64encode(b"0" * 32).decode()


def _trial_user(user_id=42):
    return User(
        id=user_id,
        email="owner@example.test",
        hashed_password="unused",
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=1),
    )


class _FakeExecuteResult:
    def __init__(self, rows=None, scalar=None, rowcount=0):
        self.rows = rows or []
        self.scalar = scalar
        self.rowcount = rowcount

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
        self.deleted_queries = []
        self.executed_queries = []
        self.committed = False
        self.commit_count = 0

    async def execute(self, _query, *_params):
        self.executed_queries.append(_query)
        if str(_query).lstrip().upper().startswith("DELETE"):
            self.deleted_queries.append(_query)
            return _FakeExecuteResult()
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
        self.commit_count += 1


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

    def test_health_endpoint_is_public_and_reports_status(self):
        webhook_main.app.dependency_overrides.clear()

        response = TestClient(webhook_main.app).get("/webhooks/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_config_returns_existing_public_endpoint_without_writing(self):
        endpoint = webhook_main.WebhookEndpoint(id=7, user_id=42, slug="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", name="Default")
        session = _FakeSession([[endpoint]])

        response = _client(session).get("/webhooks/config")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["endpoint_url"], f"{webhook_main.WEBHOOK_PUBLIC_BASE_URL}/in/{endpoint.slug}")
        self.assertEqual(session.added, [])

    def test_config_returns_empty_contract_without_endpoint(self):
        session = _FakeSession([[]])
        response = _client(session).get("/webhooks/config")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["endpoint"])
        self.assertIsNone(response.json()["endpoint_url"])
        self.assertEqual(session.added, [])

    def test_persist_records_query_ip_signature_and_alert_metadata(self):
        persisted = webhook_main.WebhookRequest(
            id=7,
            endpoint_id=99,
            user_id=42,
            method="POST",
            path="/in/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            headers_json="{}",
            body='{"type":"invoice.paid"}',
        )
        managed_session = _FakeSession([[persisted], [], []])
        signature_result = {
            "valid": False,
            "error": "signature_mismatch",
            "provider": "stripe",
            "details": {"header": "stripe-signature"},
        }

        @asynccontextmanager
        async def fake_managed_session():
            yield managed_session

        async def noop_detect(**_kwargs):
            return None

        with patch.object(webhook_main, "get_managed_session", fake_managed_session), \
                patch.object(webhook_main, "detect_and_act_on_payment", noop_detect):
            asyncio.run(
                webhook_main._persist_and_forward(
                    request_id=7,
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

        self.assertEqual(json.loads(persisted.query_params_json), {"mode": "test"})
        self.assertEqual(persisted.ip_address, "203.0.113.10")
        self.assertFalse(persisted.signature_valid)
        self.assertEqual(persisted.signature_error, "signature_mismatch")
        self.assertEqual(persisted.signature_provider, "stripe")

    def test_public_in_route_accepts_ten_megabyte_limit_contract(self):
        self.assertEqual(webhook_main.MAX_WEBHOOK_BODY_BYTES, 10 * 1024 * 1024)

    def test_ingest_persists_forward_outbox_before_returning_received(self):
        endpoint = webhook_main.WebhookEndpoint(id=99, user_id=42, slug="abc", name="Default")
        settings = webhook_main.WebhookSettings(user_id=42, forward_url="https://example.com/hook")
        session = _FakeSession([
            [endpoint],
            [settings],
            _FakeExecuteResult(scalar=0),
            _FakeExecuteResult(scalar=0),
            [],
            [],
            [settings],
        ])

        async def noop_limits(_session, _user_id):
            return "pro", SimpleNamespace(events_per_day=100)

        async def noop_detect(**_kwargs):
            return None

        with patch.object(webhook_main, "get_webhookmonitor_limits_for_user_id", noop_limits), \
                patch.object(webhook_main, "detect_and_act_on_payment", noop_detect):
            response = _client(session).post(
                "/in/abc",
                json={"type": "invoice.paid"},
                headers={"x-event-id": "evt_123"},
            )

        self.assertEqual(response.status_code, 200)
        outbox_jobs = [item for item in session.added if isinstance(item, webhook_main.SystemOutbox)]
        self.assertEqual(len(outbox_jobs), 1)
        self.assertEqual(outbox_jobs[0].job_type, "forward_webhook")
        self.assertTrue(session.committed)
        self.assertEqual(response.json()["request_id"], 1)
        self.assertEqual(response.json()["delivery_status"], "queued")

    def test_ingest_duplicate_provider_event_id_returns_ignored_without_outbox(self):
        endpoint = webhook_main.WebhookEndpoint(id=99, user_id=42, slug="abc", name="Default")
        duplicate = webhook_main.WebhookEventIdempotency(
            user_id=42,
            endpoint_id=99,
            provider_event_id="evt_123",
            request_id=77,
        )
        session = _FakeSession([
            [endpoint],
            None,
            _FakeExecuteResult(scalar=0),
            _FakeExecuteResult(scalar=0),
            [duplicate],
        ])

        async def noop_limits(_session, _user_id):
            return "pro", SimpleNamespace(events_per_day=100)

        with patch.object(webhook_main, "get_webhookmonitor_limits_for_user_id", noop_limits):
            response = _client(session).post(
                "/in/abc",
                json={"id": "evt_123", "type": "invoice.paid"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ignored")
        self.assertFalse(any(isinstance(item, webhook_main.SystemOutbox) for item in session.added))

    def test_read_body_with_limit_rejects_chunked_stream_over_limit(self):
        class ChunkedRequest:
            async def stream(self):
                yield b"123"
                yield b"456"

        with self.assertRaises(webhook_main.HTTPException) as ctx:
            asyncio.run(webhook_main._read_body_with_limit(ChunkedRequest(), 5))

        self.assertEqual(ctx.exception.status_code, 413)

    def test_delete_endpoint_does_not_delete_requests_for_foreign_endpoint(self):
        session = _FakeSession([[]])

        response = _client(session).delete("/webhooks/endpoints/99")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(session.deleted_queries, [])

    def test_delete_endpoint_removes_owned_endpoint_events_and_idempotency_rows(self):
        endpoint = webhook_main.WebhookEndpoint(id=99, user_id=42, slug="abc", name="QA")
        session = _FakeSession([[endpoint]])

        response = _client(session).delete("/webhooks/endpoints/99")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "deleted")
        deleted_sql = "\n".join(str(query) for query in session.deleted_queries)
        self.assertIn("webhook_event_idempotency", deleted_sql)
        self.assertIn("webhook_requests", deleted_sql)
        self.assertIn("webhook_endpoints", deleted_sql)

    def test_clear_history_requires_confirmation_and_deletes_owned_requests(self):
        missing = _client(_FakeSession()).delete("/webhooks/requests")
        self.assertEqual(missing.status_code, 422)

        session = _FakeSession()
        confirmed = _client(session).delete("/webhooks/requests?confirm=CONFIRM")
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(len(session.deleted_queries), 1)
        self.assertIn("webhook_requests.user_id", str(session.deleted_queries[0]))

    def test_ingestion_enforces_database_backed_per_ip_rate_limit(self):
        endpoint = webhook_main.WebhookEndpoint(id=99, user_id=42, slug="abc", name="Default")
        session = _FakeSession([
            [endpoint],
            [],
            _FakeExecuteResult(scalar=0),
            _FakeExecuteResult(scalar=webhook_main.INGESTION_IP_RATE_LIMIT_PER_MINUTE),
        ])

        async def noop_limits(_session, _user_id):
            return "pro", SimpleNamespace(events_per_day=10000)

        with patch.object(webhook_main, "get_webhookmonitor_limits_for_user_id", noop_limits):
            response = _client(session).post("/in/abc", json={"type": "invoice.paid"})

        self.assertEqual(response.status_code, 429)
        self.assertIn("ip rate limit", response.json()["detail"].lower())

    def test_persist_and_forward_requires_an_existing_request(self):
        with self.assertRaises(ValueError):
            asyncio.run(webhook_main._persist_and_forward(
                request_id=None,
                endpoint_id=99,
                user_id=42,
                method="POST",
                path="/in/abc",
                headers={},
                body="{}",
            ))

    def test_config_is_read_only_when_no_endpoint_exists(self):
        session = _FakeSession([[]])

        response = _client(session).get("/webhooks/config")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["endpoint"])
        self.assertIsNone(response.json()["endpoint_url"])
        self.assertEqual(session.added, [])

    def test_delivery_endpoint_exposes_client_confirmation_state(self):
        request = _request(7, last_retry_status=202, forward_error="")
        response = _client(_FakeSession([[request]])).get("/webhooks/requests/7/delivery")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["delivery_status"], "delivered")
        self.assertEqual(response.json()["response_status"], 202)

    def test_replay_query_overrides_are_applied_and_failure_body_is_captured(self):
        request = _request(7, query_params_json='{"source":"original"}')
        session = _FakeSession([[request]])

        class FailedClient:
            def __init__(self, timeout=None):
                self.timeout = timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def request(self, **kwargs):
                self.kwargs = kwargs
                return SimpleNamespace(status_code=502, text='{"token":"secret","reason":"bad gateway"}')

        with patch.object(webhook_main.httpx, "AsyncClient", FailedClient):
            response = _client(session).post(
                "/webhooks/requests/7/replay",
                json={"mode": "exact", "query_params": {"source": "override", "attempt": "2"}},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("source=override", response.json()["target_url"])
        self.assertIn("bad gateway", response.json()["error"])
        self.assertNotIn("secret", response.json()["error"])

    def test_batch_retry_queues_only_owned_requests(self):
        requests = [_request(7, last_retry_status=500), _request(8, last_retry_status=204, forward_error="")]
        settings = webhook_main.WebhookSettings(user_id=42, forward_url="https://example.com/hook")
        session = _FakeSession([requests, [settings]])

        response = _client(session).post("/webhooks/requests/batch-retry", json={"request_ids": [7, 8]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["queued"], [7])
        self.assertEqual(response.json()["skipped"], [8])
        self.assertEqual(len([item for item in session.added if isinstance(item, webhook_main.SystemOutbox)]), 1)

    def test_analytics_endpoint_returns_daily_aggregate_contract(self):
        session = _FakeSession([[("2026-06-20", 3, 1)]])

        response = _client(session).get("/webhooks/analytics")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["days"][0]["total"], 3)
        self.assertEqual(response.json()["days"][0]["failed"], 1)

    def test_scheduled_export_is_persisted_in_outbox(self):
        session = _FakeSession([])

        response = _client(session).post("/webhooks/exports/schedule", json={"format": "json"})

        self.assertEqual(response.status_code, 200)
        job = next(item for item in session.added if isinstance(item, webhook_main.SystemOutbox))
        self.assertEqual(job.job_type, "scheduled_webhook_export")
        self.assertEqual(job.payload["format"], "json")

    def test_delete_endpoint_removes_endpoint_and_logs(self):
        endpoint = webhook_main.WebhookEndpoint(id=99, user_id=42, slug="abc", name="Default")
        session = _FakeSession([[endpoint]])

        response = _client(session).delete("/webhooks/endpoints/99")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "deleted")
        self.assertEqual(len(session.deleted_queries), 3)

    def test_v1_aliases_cover_ingestion_and_authenticated_webhook_routes(self):
        paths = {route.path for route in webhook_main.app.routes}

        self.assertIn("/v1/in/{slug}", paths)
        self.assertIn("/v1/webhooks/config", paths)
        self.assertIn("/v1/settings/webhook-prefs", paths)

    def test_audit_helper_persists_structured_event(self):
        session = _FakeSession()

        asyncio.run(webhook_main._record_audit_event(
            session,
            user_id=42,
            action="endpoint.deleted",
            entity_type="webhook_endpoint",
            entity_id=99,
            details={"reason": "user_request"},
        ))

        event = session.added[0]
        self.assertIsInstance(event, webhook_main.WebhookAuditLog)
        self.assertEqual(event.user_id, 42)
        self.assertEqual(event.action, "endpoint.deleted")
        self.assertEqual(json.loads(event.details_json)["reason"], "user_request")

    def test_cron_rate_limit_uses_atomic_neon_upsert(self):
        session = _FakeSession([[1]])

        @asynccontextmanager
        async def fake_managed_session():
            yield session

        with patch.object(webhook_main, "get_managed_session", fake_managed_session):
            asyncio.run(webhook_main._enforce_cron_rate_limit("cleanup"))

        statement = str(session.executed_queries[0]).lower()
        self.assertIn("on conflict", statement)
        self.assertIn("returning request_count", statement)
        self.assertIn("request_count < 6", statement)

    def test_json_log_export_streams_keyset_pages(self):
        request = _request(7, request_uuid="evt-7", schema_valid=True)
        session = _FakeSession([[request], []])

        async def collect():
            chunks = []
            async for chunk in webhook_main._stream_log_export(session, 42, "json"):
                chunks.append(chunk)
            return b"".join(chunks)

        payload = json.loads(asyncio.run(collect()).decode("utf-8"))

        self.assertEqual(payload[0]["event_id"], "evt-7")
        self.assertTrue(payload[0]["schema_valid"])
        self.assertEqual(len(session.executed_queries), 1)
        self.assertIn("limit", str(session.executed_queries[0]).lower())

    def test_missing_notification_settings_emit_operational_warning(self):
        with self.assertLogs(webhook_main.logger, level="WARNING") as captured:
            asyncio.run(webhook_main._notify_webhook_issue(None, "Forward failed", "timeout"))

        self.assertIn("settings are missing", " ".join(captured.output))


class WebhookLowRiskSpecTests(unittest.TestCase):
    def test_replay_deduplication_uses_compound_index_and_replay_fk(self):
        table_args = webhook_main.WebhookRequest.__table_args__
        index_names = {getattr(item, "name", None) for item in table_args if getattr(item, "name", None)}

        self.assertIn("ix_webhook_replay_dedup", index_names)
        foreign_keys = webhook_main.WebhookRequest.__table__.c.replay_of_request_id.foreign_keys
        self.assertEqual(next(iter(foreign_keys)).target_fullname, "webhook_requests.id")

    def test_har_uses_one_utc_suffix_for_aware_datetimes(self):
        request = _request(7, received_at=datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc))

        started = webhook_main._build_har_export(request)["log"]["entries"][0]["startedDateTime"]

        self.assertEqual(started, "2026-06-20T12:00:00Z")

    def test_stripe_rejects_ambiguous_multiple_timestamps(self):
        result = webhook_main.validate_webhook_signature(
            "stripe",
            "secret",
            {"stripe-signature": "t=1,t=2,v1=abc"},
            b"{}",
        )

        self.assertFalse(result["valid"])
        self.assertEqual(result["error"], "multiple_timestamps")

    def test_openapi_export_infers_nested_array_items(self):
        request = _request(7, body='{"items":[{"amount":2,"tags":["a"]}]}')

        schema = webhook_main._build_openapi_export(request)["paths"]["/in/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"]["post"]["requestBody"]["content"]["application/json"]["schema"]

        self.assertEqual(schema["properties"]["items"]["items"]["properties"]["amount"]["type"], "integer")
        self.assertEqual(schema["properties"]["items"]["items"]["properties"]["tags"]["items"]["type"], "string")

    def test_invalid_stored_methods_fail_closed(self):
        endpoint = webhook_main.WebhookEndpoint(id=1, user_id=42, slug="abc", allowed_methods_json='["TRACE"]')

        with self.assertRaises(webhook_main.HTTPException):
            webhook_main._allowed_methods(endpoint)

    def test_diff_serializes_non_json_values(self):
        diff = webhook_main._diff_values({"when": object()}, {"when": object()})

        self.assertIsInstance(diff["changed"][0]["old_value"], str)

    def test_negative_array_indexes_are_supported(self):
        self.assertEqual(webhook_main._extract_match_value({"events": ["first", "last"]}, "$.events[-1]"), "last")

    def test_binary_payloads_are_round_trippable(self):
        raw = bytes([0, 255, 1, 2])
        stored = webhook_main._store_ingested_body(raw, "application/octet-stream")

        self.assertTrue(stored.startswith("base64:"))
        self.assertEqual(webhook_main._body_bytes(stored), raw)

    def test_multiple_signature_configs_accept_any_valid_signature(self):
        body = b"{}"
        signature = hmac.new(b"second", body, hashlib.sha256).hexdigest()

        result = webhook_main.validate_webhook_signatures(
            [{"provider": "generic", "secret": "first"}, {"provider": "generic", "secret": "second"}],
            {"x-signature": f"sha256={signature}"},
            body,
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["provider"], "generic")


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

    def test_exact_replay_to_capture_url_does_not_persist_a_second_duplicate_row(self):
        original = _request(7, path="/in/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
        session = _FakeSession([[original]])

        class FakeAsyncClient:
            def __init__(self, timeout=None):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def request(self, **kwargs):
                return SimpleNamespace(status_code=200, text='{"status":"received","request_id":88}')

        with patch.object(webhook_main.httpx, "AsyncClient", FakeAsyncClient):
            response = _client(session).post("/webhooks/events/7/replay", json={"mode": "exact"})

        self.assertEqual(response.status_code, 200)
        replay_rows = [item for item in session.added if isinstance(item, webhook_main.WebhookRequest)]
        self.assertEqual(replay_rows, [])
        self.assertEqual(response.json()["event"]["id"], 88)

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

    def test_logs_accepts_offset_and_limit(self):
        requests = [_request(i) for i in range(1, 4)]
        session = _FakeSession([requests])

        response = _client(session).get("/webhooks/logs?offset=2&limit=3")

        self.assertEqual(response.status_code, 200)
        query_text = str(session.executed_queries[-1]).lower()
        self.assertIn("limit", query_text)
        self.assertIn("offset", query_text)

    def test_endpoint_events_filters_status_before_pagination(self):
        endpoint = webhook_main.WebhookEndpoint(id=99, user_id=42, slug="abc", name="Default")
        session = _FakeSession([[endpoint], [_request(8, last_retry_status=202)]])

        response = _client(session).get("/webhooks/endpoints/99/events?status=successful&limit=5&offset=1")

        self.assertEqual(response.status_code, 200)
        query_text = str(session.executed_queries[-1]).lower()
        self.assertIn("last_retry_status", query_text)
        self.assertIn("limit", query_text)
        self.assertIn("offset", query_text)

    def test_search_accepts_offset_and_limit(self):
        session = _FakeSession([[_request(8, last_retry_status=202)]])

        response = _client(session).post(
            "/webhooks/search",
            json={"status": "successful", "limit": 5, "offset": 2},
        )

        self.assertEqual(response.status_code, 200)
        query_text = str(session.executed_queries[-1]).lower()
        self.assertIn("limit", query_text)
        self.assertIn("offset", query_text)

    def test_metrics_endpoint_reports_counts(self):
        session = _FakeSession([
            _FakeExecuteResult(scalar=4),
            _FakeExecuteResult(scalar=1),
            _FakeExecuteResult(scalar=2),
            _FakeExecuteResult(scalar=1),
        ])

        response = _client(session).get("/webhooks/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 4)
        self.assertEqual(response.json()["failed"], 1)
        self.assertEqual(response.json()["successful"], 2)
        self.assertEqual(response.json()["pending"], 1)


class WebhookForwardingSpecTests(unittest.TestCase):
    def test_process_webhook_forward_returns_failed_payload_for_downstream_500(self):
        request = _request(
            7,
            last_retry_status=None,
            retry_count=0,
            forward_error="",
        )
        managed_session = _FakeSession([[request], []])

        @asynccontextmanager
        async def fake_managed_session():
            yield managed_session

        class FakeAsyncClient:
            def __init__(self, timeout=None):
                self.timeout = timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def request(self, **kwargs):
                return SimpleNamespace(status_code=500, text="downstream exploded")

        with patch.object(webhook_main, "get_managed_session", fake_managed_session), \
                patch.object(webhook_main.httpx, "AsyncClient", FakeAsyncClient):
            result = asyncio.run(webhook_main.process_webhook_forward({
                "request_id": request.id,
                "forward_url": "https://example.com/webhook",
                "max_attempts": 3,
            }))

        self.assertEqual(result["status"], "failed")
        self.assertIn("Forward returned 500", result["reason"])
        self.assertEqual(result["response_status"], 500)
        self.assertEqual(request.last_retry_status, 500)
        self.assertEqual(request.forward_error, "Forward returned 500")
        self.assertFalse(managed_session.committed)

    def test_process_webhook_forward_preserves_safe_headers_only(self):
        request = _request(
            8,
            headers_json=json.dumps({
                "content-type": "application/json",
                "stripe-signature": "t=1,v1=sig",
                "x-webhook-id": "evt_123",
                "host": "internal.test",
                "content-length": "999",
                "transfer-encoding": "chunked",
                "connection": "keep-alive",
            }),
            last_retry_status=None,
            retry_count=0,
            forward_error="",
        )
        managed_session = _FakeSession([[request], []])
        calls = []

        @asynccontextmanager
        async def fake_managed_session():
            yield managed_session

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

        with patch.object(webhook_main, "get_managed_session", fake_managed_session), \
                patch.object(webhook_main.httpx, "AsyncClient", FakeAsyncClient):
            result = asyncio.run(webhook_main.process_webhook_forward({
                "request_id": request.id,
                "forward_url": "https://example.com/webhook",
            }))

        self.assertEqual(result["status"], "success")
        forwarded_headers = calls[0]["headers"]
        self.assertEqual(forwarded_headers["content-type"], "application/json")
        self.assertEqual(forwarded_headers["stripe-signature"], "t=1,v1=sig")
        self.assertEqual(forwarded_headers["x-webhook-id"], "evt_123")
        self.assertNotIn("host", forwarded_headers)
        self.assertNotIn("content-length", forwarded_headers)
        self.assertNotIn("transfer-encoding", forwarded_headers)
        self.assertNotIn("connection", forwarded_headers)

    def test_retry_request_rejects_successful_delivery_without_forward_error(self):
        request = _request(7, last_retry_status=204, forward_error="")
        session = _FakeSession([[request]])

        response = _client(session).post("/webhooks/requests/7/retry", json={})

        self.assertEqual(response.status_code, 400)
        self.assertIn("successful", response.json()["detail"].lower())

    def test_process_scheduled_retries_uses_bounded_limit(self):
        managed_session = _FakeSession([[]])

        @asynccontextmanager
        async def fake_managed_session():
            yield managed_session

        with patch.object(webhook_main, "get_managed_session", fake_managed_session):
            asyncio.run(webhook_main.process_scheduled_retries())

        query_text = str(managed_session.executed_queries[0]).lower()
        self.assertIn("limit", query_text)

    def test_process_webhook_forward_returns_classified_timeout_without_raising(self):
        request = _request(9, last_retry_status=None, retry_count=0, forward_error="")
        managed_session = _FakeSession([[request], []])

        @asynccontextmanager
        async def fake_managed_session():
            yield managed_session

        class TimeoutClient:
            def __init__(self, timeout=None):
                self.timeout = timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def request(self, **_kwargs):
                request_info = webhook_main.httpx.Request("POST", "https://example.com/webhook")
                raise webhook_main.httpx.ReadTimeout("downstream stalled", request=request_info)

        with patch.object(webhook_main, "get_managed_session", fake_managed_session), \
                patch.object(webhook_main.httpx, "AsyncClient", TimeoutClient):
            result = asyncio.run(webhook_main.process_webhook_forward({
                "request_id": request.id,
                "forward_url": "https://example.com/webhook",
                "max_attempts": 3,
            }))

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason_code"], "timeout")
        self.assertIn("timed out", result["reason"].lower())
        self.assertFalse(managed_session.committed)

    def test_request_error_classifier_distinguishes_dns_and_refused_connections(self):
        request_info = webhook_main.httpx.Request("POST", "https://example.com/webhook")
        dns_error = webhook_main.httpx.ConnectError("dns", request=request_info)
        dns_error.__cause__ = OSError(11001, "host not found")
        refused_error = webhook_main.httpx.ConnectError("refused", request=request_info)
        refused_error.__cause__ = ConnectionRefusedError(10061, "connection refused")

        self.assertEqual(webhook_main._request_error_code(dns_error), "dns_failure")
        self.assertEqual(webhook_main._request_error_code(refused_error), "connection_refused")

    def test_cleanup_old_logs_deletes_once_per_retention_group(self):
        managed_session = _FakeSession([[1, 2, 3], []])

        @asynccontextmanager
        async def fake_managed_session():
            yield managed_session

        with patch.object(webhook_main, "get_managed_session", fake_managed_session):
            asyncio.run(webhook_main.cleanup_old_logs())

        self.assertEqual(len(managed_session.deleted_queries), 1)
        self.assertIn(" IN ", str(managed_session.deleted_queries[0]).upper())


class WebhookCryptoSpecTests(unittest.TestCase):
    def test_get_fernets_returns_immutable_cached_collection(self):
        webhook_main.IntegrationsCrypto._cached_env_key = None
        webhook_main.IntegrationsCrypto._fernets = []

        with patch.dict(webhook_main.os.environ, {"ENCRYPTION_KEY": TEST_ENCRYPTION_KEY}, clear=False):
            fernets = webhook_main.IntegrationsCrypto.get_fernets()
            with self.assertRaises(AttributeError):
                fernets.append("not-a-fernet")
            self.assertNotIn("not-a-fernet", webhook_main.IntegrationsCrypto.get_fernets())

    def test_crypto_rejects_missing_encryption_key(self):
        webhook_main.IntegrationsCrypto._cached_env_key = None
        webhook_main.IntegrationsCrypto._fernets = ()

        with patch.dict(webhook_main.os.environ, {"ENCRYPTION_KEY": ""}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "ENCRYPTION_KEY"):
                webhook_main.IntegrationsCrypto.get_fernets()

    def test_json_parser_does_not_hide_unexpected_runtime_errors(self):
        with patch.object(webhook_main.json, "loads", side_effect=RuntimeError("unexpected parser failure")):
            with self.assertRaises(RuntimeError):
                webhook_main._parse_json_or_text("{}")

    def test_compiled_json_schema_is_cached_by_schema_text(self):
        schema_text = json.dumps({"type": "object", "properties": {"id": {"type": "string"}}})
        webhook_main._cached_schema_validator.cache_clear()

        first = webhook_main._cached_schema_validator(schema_text)
        second = webhook_main._cached_schema_validator(schema_text)

        self.assertIs(first, second)


if __name__ == "__main__":
    unittest.main()
