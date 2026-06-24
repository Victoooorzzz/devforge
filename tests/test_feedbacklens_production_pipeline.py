import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

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
    def __init__(self, rows=None, item=None, responses=None):
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


class FeedbackLensProductionPipelineTests(unittest.TestCase):
    def tearDown(self):
        feedback_main.app.dependency_overrides.clear()

    def test_feedbacklens_uses_local_analysis_without_gemini_or_ai_copy(self):
        backend = (ROOT / "apps" / "feedbacklens" / "backend" / "main.py").read_text(encoding="utf-8")
        product = (ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "config" / "product.ts").read_text(encoding="utf-8")
        landing = (ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "app" / "page.tsx").read_text(encoding="utf-8")
        settings = (ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "app" / "dashboard" / "settings" / "page.tsx").read_text(encoding="utf-8")

        for text in (backend, product, landing, settings):
            self.assertNotIn("Gemini", text)
            self.assertNotIn("genai", text)
            self.assertNotIn("AI-Powered", text)
            self.assertNotIn("AI analysis", text)
        self.assertIn("Local sentiment analysis", product)
        self.assertIn("Local Analysis Preferences", settings)

    def test_analyze_and_draft_reply_are_local_and_deterministic(self):
        entry = feedback_main.FeedbackEntry(
            id=7,
            user_id=42,
            text="Export is broken and I need a refund urgently",
            created_at=datetime.utcnow(),
        )
        session = _FakeSession(responses=[[entry], []], item=entry)
        client = _client(session)

        analyzed = client.post("/feedback/7/analyze")
        drafted = client.post("/feedback/7/draft-reply")

        self.assertEqual(analyzed.status_code, 200)
        self.assertEqual(drafted.status_code, 200)
        self.assertIn(analyzed.json()["analysis_engine"], {"vader", "keyword"})
        self.assertNotEqual(analyzed.json()["analysis_engine"], "gemini")
        self.assertTrue(drafted.json()["draft_reply"])
        self.assertNotIn("Gemini", drafted.json()["draft_reply"])

    def test_dedupe_summary_endpoint_groups_near_duplicates(self):
        rows = [
            SimpleNamespace(id=1, text="Checkout crashes when I add my card", created_at=datetime.utcnow()),
            SimpleNamespace(id=2, text="The checkout crashed after adding a card", created_at=datetime.utcnow()),
            SimpleNamespace(id=3, text="Weekly summary is useful", created_at=datetime.utcnow()),
        ]
        response = _client(_FakeSession(rows=rows)).get("/feedback/dedupe/summary")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_feedback"], 3)
        self.assertEqual(payload["duplicate_groups"], 1)
        self.assertEqual(payload["duplicate_candidates"], 2)
        self.assertGreater(payload["dedupe_rate"], 0)
        self.assertEqual(payload["groups"][0]["canonical_id"], 1)

    def test_frontend_contract_docs_exist_for_feedbacklens(self):
        contract = ROOT / "docs" / "features" / "feedbacklens-frontend-contract.md"
        pipeline = ROOT / "docs" / "features" / "feedbacklens-production-pipeline.md"

        self.assertTrue(contract.exists())
        self.assertTrue(pipeline.exists())
        self.assertIn("/feedback/dedupe/summary", contract.read_text(encoding="utf-8"))
        self.assertIn("Local sentiment analysis", pipeline.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
