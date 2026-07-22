import hashlib
import hmac
import asyncio
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

import apps.feedbacklens.backend.main as feedback_main
from backend_core.auth import User, get_current_user
from backend_core.database import get_session
from backend_core.outbox_models import SystemOutbox


class _FakeExecuteResult:
    def __init__(self, rows=None, scalar=None):
        self.rows = list(rows or [])
        self.scalar = scalar

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None

    def first(self):
        return self.rows[0] if self.rows else None

    def scalar_one(self):
        return self.scalar if self.scalar is not None else len(self.rows)


class _FakeSession:
    def __init__(self, responses=None):
        self.responses = [list(response) for response in (responses or [])]
        self.added = []
        self.committed = False
        self.flushed = False

    async def execute(self, _query):
        if self.responses:
            return _FakeExecuteResult(self.responses.pop(0))
        return _FakeExecuteResult([])

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flushed = True
        for index, item in enumerate(self.added, start=100):
            if getattr(item, "id", None) is None:
                item.id = index

    async def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = 100

    async def commit(self):
        self.committed = True


def _trial_user():
    return User(
        id=42,
        email="owner@example.test",
        hashed_password="unused",
        trial_ends_at=datetime.utcnow() + timedelta(days=1),
    )


def _paid_user():
    user = _trial_user()
    user.is_active = True
    return user


def _client(session):
    return _client_for_user(session, _trial_user)


def _paid_client(session):
    return _client_for_user(session, _paid_user)


def _client_for_user(session, user_factory):
    feedback_main.app.dependency_overrides.clear()
    feedback_main.app.dependency_overrides[get_current_user] = user_factory

    async def override_session():
        yield session

    feedback_main.app.dependency_overrides[get_session] = override_session
    return TestClient(feedback_main.app)


class FeedbackLensCollectionPipelineTests(unittest.TestCase):
    def tearDown(self):
        feedback_main.app.dependency_overrides.clear()
        os.environ.pop("CRON_SECRET", None)

    def test_get_feedback_alias_filters_by_priority_and_source(self):
        rows = [
            feedback_main.FeedbackEntry(
                id=1,
                user_id=42,
                text="Checkout is broken",
                source="github",
                priority="urgent",
                created_at=datetime.utcnow(),
            )
        ]

        response = _client(_FakeSession(responses=[rows])).get("/feedback?priority=urgent&source=github")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["id"], 1)
        self.assertEqual(response.json()[0]["priority"], "urgent")

    def test_cleanup_rejects_spam_truncates_and_queues_urgent_alert(self):
        prefs = feedback_main.FeedbackSettings(user_id=42, alert_email="alerts@example.test")
        long_context = "Intro sentence. " * 220
        body = f"{long_context} Checkout is broken and I need a refund urgently. https://shop.example/product"
        session = _FakeSession(responses=[[], [], [], [prefs]])

        response = _client(session).post(
            "/feedback/ingest/email",
            json={
                "from_email": "customer@example.test",
                "subject": "Payment problem",
                "body": body,
                "message_id": "email-1",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertLessEqual(len(payload["text"]), 2000)
        self.assertIn("Checkout is broken", payload["text"])
        self.assertTrue(payload["is_urgent"])
        queued = [item for item in session.added if isinstance(item, SystemOutbox)]
        self.assertEqual(len(queued), 1)
        self.assertEqual(queued[0].app_name, "feedbacklens")
        self.assertEqual(queued[0].job_type, "send_email")
        self.assertIn("Urgent feedback", queued[0].payload["subject"])

    def test_spam_feedback_is_rejected_before_storage(self):
        response = _client(_FakeSession()).post(
            "/feedback",
            json={"text": "buy now click here free money http://spam.example http://bad.example"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("spam", response.json()["detail"].lower())

    def test_cron_poll_sources_ingests_due_external_sources(self):
        sources = [
            feedback_main.FeedbackSource(id=1, user_id=42, source_type="twitter", display_name="X", access_token="token", handle="@product"),
            feedback_main.FeedbackSource(id=2, user_id=42, source_type="reddit", display_name="Reddit", access_token="token", handle="product"),
            feedback_main.FeedbackSource(id=3, user_id=42, source_type="github", display_name="GitHub", access_token="token", config_json=json.dumps({"repo": "acme/app"})),
        ]
        session = _FakeSession(responses=[sources, [], [], [], [], [], []])

        def fake_managed_session():
            class _Context:
                async def __aenter__(self):
                    return session

                async def __aexit__(self, *_args):
                    return False

            return _Context()

        async def fake_poll(source):
            return [{
                "text": f"{source.source_type} says checkout is broken",
                "author": source.display_name,
                "source_url": f"https://example.test/{source.source_type}",
                "source_message_id": f"{source.source_type}-1",
            }]

        with patch.object(feedback_main, "get_managed_session", fake_managed_session), patch.object(feedback_main, "_poll_source_feedback", fake_poll):
            response = TestClient(feedback_main.app).post("/feedback/cron/poll")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ingested"], 3)
        self.assertTrue(all(source.last_polled_at for source in sources))
        self.assertEqual(len([item for item in session.added if isinstance(item, feedback_main.FeedbackEntry)]), 3)
        self.assertTrue(session.committed)

    def test_github_webhook_validates_signature_and_ingests_issue(self):
        source = feedback_main.FeedbackSource(
            id=9,
            user_id=42,
            source_type="github",
            display_name="GitHub",
            webhook_secret="secret",
            status="connected",
        )
        body = {
            "action": "opened",
            "issue": {
                "id": 123,
                "title": "Export keeps failing",
                "body": "Large CSV export crashes every time.",
                "html_url": "https://github.com/acme/app/issues/1",
                "user": {"login": "octo"},
            },
            "repository": {"full_name": "acme/app"},
        }
        raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
        signature = hmac.new(b"secret", raw, hashlib.sha256).hexdigest()

        response = _client(_FakeSession(responses=[[source], []])).post(
            "/feedback/ingest/github?source_id=9",
            content=raw,
            headers={"x-hub-signature-256": f"sha256={signature}", "content-type": "application/json"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "github")
        self.assertEqual(response.json()["author"], "octo")

    def test_github_oauth_callback_exchanges_code_and_marks_source_connected(self):
        source = feedback_main.FeedbackSource(
            id=7,
            user_id=42,
            source_type="github",
            display_name="GitHub",
            status="pending_oauth",
            config_json=json.dumps({"oauth_state": "state-1", "repo": "acme/app"}),
        )

        with patch.dict(os.environ, {"ENCRYPTION_KEY": "feedbacklens-test-key"}, clear=False), \
                patch.object(
                    feedback_main,
                    "_exchange_oauth_code",
                    return_value={"access_token": "gho_token", "refresh_token": "refresh"},
                ):
            response = _client(_FakeSession(responses=[[source]])).get("/connect/github/callback?state=state-1&code=abc")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "connected")
        self.assertTrue(source.access_token.startswith("enc:"))
        with patch.dict(os.environ, {"ENCRYPTION_KEY": "feedbacklens-test-key"}, clear=False):
            self.assertEqual(feedback_main.decrypt_secret(source.access_token), "gho_token")
        self.assertEqual(source.status, "connected")

    def test_email_ingest_extracts_text_attachments(self):
        session = _FakeSession(responses=[[]])

        response = _client(session).post(
            "/feedback/ingest/email",
            json={
                "from_email": "customer@example.test",
                "subject": "Details attached",
                "body": "The full feedback is attached.",
                "message_id": "email-attachment-1",
                "attachments": [
                    {
                        "filename": "export-feedback.txt",
                        "content_type": "text/plain",
                        "text": "Export fails whenever the CSV has more than 100 rows.",
                    }
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Export fails", response.json()["text"])
        self.assertEqual(response.json()["source"], "email")

    def test_bulk_import_runs_cleanup_analysis_and_urgent_alerts(self):
        prefs = feedback_main.FeedbackSettings(user_id=42, alert_email="alerts@example.test")
        session = _FakeSession(responses=[[], [], [prefs], []])

        response = _client(session).post(
            "/feedback/bulk",
            json={
                "texts": [
                    "buy now click here free money http://spam.example http://bad.example",
                    "Checkout is broken and I need a refund urgently.",
                    "The weekly summary is useful and clear.",
                ]
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["created"], 2)
        self.assertEqual(payload["spam_rejected"], 1)
        created_entries = [item for item in session.added if isinstance(item, feedback_main.FeedbackEntry)]
        self.assertEqual(len(created_entries), 2)
        self.assertTrue(all(entry.sentiment for entry in created_entries))
        self.assertTrue(all(entry.cluster_slug for entry in created_entries))
        self.assertEqual(len([item for item in session.added if isinstance(item, SystemOutbox)]), 1)

    def test_source_message_id_duplicate_returns_existing_entry(self):
        source = feedback_main.FeedbackSource(
            id=9,
            user_id=42,
            source_type="github",
            display_name="GitHub",
            webhook_secret="secret",
            status="connected",
        )
        existing = feedback_main.FeedbackEntry(
            id=33,
            user_id=42,
            text="Initial issue text",
            source="github",
            source_message_id="123",
            created_at=datetime.utcnow(),
        )
        body = {
            "action": "edited",
            "issue": {
                "id": 123,
                "title": "Completely different updated report",
                "body": "The new body is not semantically close to the old one.",
                "html_url": "https://github.com/acme/app/issues/1",
                "user": {"login": "octo"},
            },
        }
        raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
        signature = hmac.new(b"secret", raw, hashlib.sha256).hexdigest()

        response = _client(_FakeSession(responses=[[source], [], [existing]])).post(
            "/feedback/ingest/github?source_id=9",
            content=raw,
            headers={"x-hub-signature-256": f"sha256={signature}", "content-type": "application/json"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["deduped"])
        self.assertEqual(response.json()["duplicate_of_id"], 33)

    def test_twitter_and_reddit_oauth_callbacks_store_tokens(self):
        with patch.dict(
            os.environ,
            {
                "FEEDBACKLENS_TWITTER_CLIENT_ID": "tw-client",
                "FEEDBACKLENS_TWITTER_REDIRECT_URI": "https://app.example/connect/twitter/callback",
                "FEEDBACKLENS_REDDIT_CLIENT_ID": "rd-client",
                "FEEDBACKLENS_REDDIT_REDIRECT_URI": "https://app.example/connect/reddit/callback",
            },
            clear=False,
        ):
            twitter_start = _paid_client(_FakeSession(responses=[[]])).post(
                "/connect/twitter",
                json={"handle": "@product", "query": "@product"},
            )
            reddit_start = _paid_client(_FakeSession(responses=[[]])).post(
                "/connect/reddit",
                json={"subreddit": "SaaS", "query": "FeedbackLens"},
            )

        self.assertEqual(twitter_start.status_code, 200)
        self.assertIn("x.com/i/oauth2/authorize", twitter_start.json()["authorization_url"])
        self.assertIn("code_challenge=", twitter_start.json()["authorization_url"])
        self.assertEqual(reddit_start.status_code, 200)
        self.assertIn("reddit.com/api/v1/authorize", reddit_start.json()["authorization_url"])

        twitter_source = feedback_main.FeedbackSource(
            id=11,
            user_id=42,
            source_type="twitter",
            status="pending_oauth",
            config_json=json.dumps({"oauth_state": "tw-state", "code_verifier": "verifier", "redirect_uri": ""}),
        )
        reddit_source = feedback_main.FeedbackSource(
            id=12,
            user_id=42,
            source_type="reddit",
            status="pending_oauth",
            config_json=json.dumps({"oauth_state": "rd-state", "redirect_uri": ""}),
        )

        with patch.dict(os.environ, {"ENCRYPTION_KEY": "feedbacklens-test-key"}, clear=False), \
                patch.object(feedback_main, "_exchange_oauth_code", return_value={"access_token": "token", "refresh_token": "refresh"}):
            twitter_callback = _paid_client(_FakeSession(responses=[[twitter_source]])).get(
                "/connect/twitter/callback?state=tw-state&code=abc"
            )
            reddit_callback = _paid_client(_FakeSession(responses=[[reddit_source]])).get(
                "/connect/reddit/callback?state=rd-state&code=def"
            )

        self.assertEqual(twitter_callback.status_code, 200)
        self.assertEqual(reddit_callback.status_code, 200)
        self.assertEqual(twitter_source.status, "connected")
        self.assertEqual(reddit_source.status, "connected")
        self.assertTrue(twitter_source.access_token.startswith("enc:"))
        self.assertTrue(reddit_source.refresh_token.startswith("enc:"))
        with patch.dict(os.environ, {"ENCRYPTION_KEY": "feedbacklens-test-key"}, clear=False):
            self.assertEqual(feedback_main.decrypt_secret(twitter_source.access_token), "token")
            self.assertEqual(feedback_main.decrypt_secret(reddit_source.refresh_token), "refresh")

    def test_free_plan_rejects_external_sources_and_documents_limits(self):
        from backend_core.plan_limits import FEEDBACKLENS_LIMITS

        self.assertEqual(FEEDBACKLENS_LIMITS["free"].max_feedback_per_month, 100)
        self.assertNotIn("twitter", FEEDBACKLENS_LIMITS["free"].allowed_sources)

        response = _client(_FakeSession(responses=[[]])).post(
            "/sources",
            json={"source_type": "twitter", "display_name": "X", "handle": "@product", "access_token": "token"},
        )

        self.assertEqual(response.status_code, 429)
        self.assertIn("Free plan", response.json()["detail"])

    def test_delete_source_disconnects_credentials_but_keeps_feedback_history(self):
        source = feedback_main.FeedbackSource(
            id=5,
            user_id=42,
            source_type="twitter",
            display_name="X",
            access_token="secret-token",
            refresh_token="secret-refresh",
            webhook_secret="webhook-secret",
            status="connected",
        )

        response = _client(_FakeSession(responses=[[source]])).delete("/sources/5")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "deleted")
        self.assertEqual(response.json()["feedback_retention"], "kept")
        self.assertEqual(source.access_token, "")
        self.assertEqual(source.refresh_token, "")
        self.assertEqual(source.webhook_secret, "")

    def test_weekly_summary_cron_respects_monday_9am_user_timezone(self):
        prefs = feedback_main.FeedbackSettings(user_id=42, alert_email="alerts@example.test")
        prefs.timezone = "America/Lima"
        entry = feedback_main.FeedbackEntry(
            id=1,
            user_id=42,
            text="Checkout is broken",
            sentiment="negative",
            is_urgent=True,
            created_at=datetime.utcnow(),
        )
        session = _FakeSession(responses=[[prefs], [entry]])
        sent = []

        def fake_managed_session():
            class _Context:
                async def __aenter__(self):
                    return session

                async def __aexit__(self, *_args):
                    return False

            return _Context()

        with patch.object(feedback_main, "get_managed_session", fake_managed_session), patch.object(
            feedback_main,
            "send_email",
            lambda **kwargs: sent.append(kwargs),
        ):
            asyncio.run(feedback_main.weekly_summary_cron(now=datetime(2026, 6, 22, 14, 5, tzinfo=timezone.utc)))

        self.assertEqual(len(sent), 1)
        self.assertIsNotNone(prefs.last_weekly_digest_at)

    def test_universal_periodic_worker_runs_feedbacklens_polling(self):
        universal_main = (ROOT / "packages" / "backend_core" / "universal_main.py").read_text(encoding="utf-8")

        self.assertIn("poll_feedback_sources", universal_main)
        self.assertIn('"source_polling"', universal_main)


if __name__ == "__main__":
    unittest.main()
