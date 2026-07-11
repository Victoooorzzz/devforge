import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
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


class _FakeExecuteResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class _FakeSession:
    def __init__(self, rows=None, responses=None, item=None):
        self.rows = list(rows or [])
        self.responses = [list(response) for response in (responses or [])]
        self.item = item
        self.added = []
        self.committed = False

    async def execute(self, _query):
        if self.responses:
            return _FakeExecuteResult(self.responses.pop(0))
        return _FakeExecuteResult(self.rows)

    async def get(self, _model, _item_id):
        return self.item

    def add(self, item):
        self.added.append(item)

    async def flush(self):
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


def _client(session):
    feedback_main.app.dependency_overrides.clear()
    feedback_main.app.dependency_overrides[get_current_user] = _trial_user

    async def override_session():
        yield session

    feedback_main.app.dependency_overrides[get_session] = override_session
    return TestClient(feedback_main.app)


def _entry(entry_id, text, *, sentiment="negative", urgent=False, source="manual", themes=None):
    entry = feedback_main.FeedbackEntry(
        id=entry_id,
        user_id=42,
        text=text,
        sentiment=sentiment,
        confidence=0.8,
        is_urgent=urgent,
        themes_json=json.dumps(themes or []),
        source=source,
        author=f"{source}-user",
        source_url=f"https://example.test/{entry_id}",
        created_at=datetime.utcnow(),
    )
    analysis = feedback_main._analyze_feedback_locally(text)
    entry.cluster_slug = feedback_main._cluster_slug_for_analysis(text, analysis["themes"])
    entry.priority = feedback_main._priority_for_analysis(analysis)
    return entry


class FeedbackLensSourcesClustersCliTests(unittest.TestCase):
    def tearDown(self):
        feedback_main.app.dependency_overrides.clear()

    def test_sources_and_webhook_ingest_routes_are_live(self):
        session = _FakeSession(responses=[[], []])
        client = _client(session)

        source_response = client.post(
            "/sources",
            json={"source_type": "email", "display_name": "Support inbox"},
        )
        email_response = client.post(
            "/feedback/ingest/email",
            json={
                "from_email": "customer@example.test",
                "subject": "Export is broken",
                "body": "Export keeps failing on large CSV files.",
                "message_id": "msg-1",
            },
        )
        canny_response = client.post(
            "/feedback/ingest/canny",
            json={
                "author": "Lee",
                "title": "Dark mode",
                "body": "Please add dark mode for the dashboard.",
                "url": "https://canny.example/post/1",
            },
        )

        self.assertEqual(source_response.status_code, 200)
        self.assertEqual(source_response.json()["source_type"], "email")
        self.assertIn("feedback-", source_response.json()["forward_address"])
        self.assertEqual(email_response.status_code, 200)
        self.assertEqual(email_response.json()["source"], "email")
        self.assertEqual(email_response.json()["author"], "customer@example.test")
        self.assertEqual(canny_response.status_code, 200)
        self.assertEqual(canny_response.json()["source"], "canny")

    def test_clusters_digest_and_github_issue_are_backed_by_entries(self):
        entries = [
            _entry(1, "Checkout crashes when I add my card", urgent=True, source="github", themes=["checkout", "crash"]),
            _entry(2, "The checkout crashed after adding a card", urgent=True, source="email", themes=["checkout", "crash"]),
            _entry(3, "Weekly summary is useful", sentiment="positive", source="manual", themes=["summary"]),
        ]
        github_source = feedback_main.FeedbackSource(
            id=10,
            user_id=42,
            source_type="github",
            display_name="GitHub",
            access_token="ghp_test",
            config_json=json.dumps({"repo": "acme/app"}),
            status="connected",
        )
        created_issue = {}

        def fake_issue(repo, token, payload):
            created_issue.update({"repo": repo, "token": token, "payload": payload})
            return {"html_url": "https://github.com/acme/app/issues/123", "number": 123}

        client = _client(_FakeSession(responses=[entries, entries, entries, [github_source]]))
        with patch.object(feedback_main, "_post_github_issue", fake_issue):
            clusters = client.get("/clusters")
            digest = client.get("/digest")
            issue = client.post("/clusters/checkout/github-issue", json={"repo": "acme/app"})

        self.assertEqual(clusters.status_code, 200)
        self.assertEqual(clusters.json()["clusters"][0]["id"], "checkout")
        self.assertEqual(clusters.json()["clusters"][0]["priority"], "urgent")
        self.assertEqual(digest.status_code, 200)
        self.assertEqual(digest.json()["summary"]["total_feedback"], 3)
        self.assertEqual(digest.json()["urgent"][0]["id"], "checkout")
        self.assertEqual(issue.status_code, 200)
        self.assertEqual(issue.json()["issue_url"], "https://github.com/acme/app/issues/123")
        self.assertEqual(created_issue["repo"], "acme/app")
        self.assertIn("Checkout crashes", created_issue["payload"]["body"])

    def test_feedbacklens_cli_maps_spec_commands_to_api_contract(self):
        import apps.feedbacklens.cli.feedbacklens as cli

        calls = []

        def fake_request(method, path, payload):
            calls.append((method, path, payload))
            return {"ok": True}

        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            os.environ,
            {"FEEDBACKLENS_CONFIG_DIR": temp_dir, "FEEDBACKLENS_API_KEY": "test-key"},
            clear=False,
        ):
            self.assertEqual(cli.run(["login", "--api-key", "KEY"])["status"], "ok")
            cli.run(["sources", "add", "--type", "twitter", "--handle", "@myproduct"], fake_request)
            cli.run(["feedback", "list", "--priority", "urgent"], fake_request)
            cli.run(["clusters", "list", "--days", "7"], fake_request)
            cli.run(["clusters", "create-issue", "--id", "checkout", "--repo", "acme/app"], fake_request)

        self.assertEqual(calls[0], ("POST", "/sources", {"source_type": "twitter", "display_name": "@myproduct", "handle": "@myproduct"}))
        self.assertEqual(calls[1], ("GET", "/feedback/list?priority=urgent", None))
        self.assertEqual(calls[2], ("GET", "/clusters?days=7", None))
        self.assertEqual(calls[3], ("POST", "/clusters/checkout/github-issue", {"repo": "acme/app"}))


if __name__ == "__main__":
    unittest.main()
