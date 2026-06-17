import io
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

from apps.feedbacklens.backend.main import FeedbackEntry, app as feedback_app
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
    def __init__(self, existing_entries):
        self.existing_entries = list(existing_entries)
        self.added = []
        self.flushed = False
        self.committed = False
        self.next_id = 100

    async def execute(self, _query):
        return _FakeExecuteResult(self.existing_entries)

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flushed = True
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = self.next_id
                self.next_id += 1

    async def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = self.next_id
            self.next_id += 1

    async def commit(self):
        self.committed = True


def _trial_user():
    return User(
        id=42,
        email="owner@example.test",
        hashed_password="unused",
        trial_ends_at=datetime.utcnow() + timedelta(days=1),
    )


def _existing_feedback(text: str, entry_id: int = 9):
    return FeedbackEntry(
        id=entry_id,
        user_id=42,
        text=text,
        sentiment="negative",
        confidence=0.86,
        themes_json='["checkout"]',
        is_urgent=True,
        draft_reply="We are checking this.",
        analysis_engine="keyword",
        created_at=datetime.utcnow(),
    )


def _override_app(session):
    feedback_app.dependency_overrides.clear()
    feedback_app.dependency_overrides[get_current_user] = _trial_user

    async def override_session():
        yield session

    feedback_app.dependency_overrides[get_session] = override_session


class FeedbackLensDedupeIntegrationTests(unittest.TestCase):
    def tearDown(self):
        feedback_app.dependency_overrides.clear()

    def test_create_feedback_returns_existing_semantic_duplicate(self):
        session = _FakeSession([
            _existing_feedback("Checkout crashes when I add my card"),
        ])
        _override_app(session)

        response = TestClient(feedback_app).post(
            "/feedback",
            json={"text": "The checkout crashed after adding a card."},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], 9)
        self.assertTrue(payload["deduped"])
        self.assertEqual(payload["duplicate_of_id"], 9)
        self.assertEqual(session.added, [])

    def test_bulk_import_skips_existing_and_in_batch_semantic_duplicates(self):
        session = _FakeSession([
            _existing_feedback("Invoice export fails for big accounts"),
        ])
        _override_app(session)

        response = TestClient(feedback_app).post(
            "/feedback/bulk",
            json={
                "texts": [
                    "Exporting invoices fails on large accounts",
                    "I love the weekly summary dashboard",
                    "Love weekly summaries in the dashboard",
                ]
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["created"], 1)
        self.assertEqual(payload["duplicates_skipped"], 2)
        self.assertEqual(len(payload["ids"]), 1)
        self.assertEqual(len(session.added), 1)
        self.assertTrue(session.committed)

    def test_bulk_csv_skips_semantic_duplicates(self):
        session = _FakeSession([
            _existing_feedback("Billing page is confusing and slow"),
        ])
        _override_app(session)
        csv_content = (
            "text\n"
            "The billing screen feels slow and confusing\n"
            "Search filters are fast and useful\n"
        ).encode("utf-8")

        response = TestClient(feedback_app).post(
            "/feedback/bulk-csv",
            files={"file": ("feedback.csv", io.BytesIO(csv_content), "text/csv")},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["created"], 1)
        self.assertEqual(payload["duplicates_skipped"], 1)
        self.assertEqual(payload["total_rows"], 2)
        self.assertEqual(len(session.added), 1)


if __name__ == "__main__":
    unittest.main()
