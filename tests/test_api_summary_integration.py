import sys
import unittest
import io
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

from fastapi.testclient import TestClient
from PIL import Image

from apps.feedbacklens.backend.main import app as feedback_app
from apps.filecleaner.backend.main import app as file_app
from apps.invoicefollow.backend.main import app as invoice_app
from apps.pricetrackr.backend.main import app as tracker_app
from apps.webhookmonitor.backend.main import app as webhook_app
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
    def __init__(self, responses):
        self.responses = list(responses)
        self.added = []

    async def execute(self, _query):
        if not self.responses:
            raise AssertionError("Unexpected query in summary endpoint")
        return _FakeExecuteResult(self.responses.pop(0))

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        for index, item in enumerate(self.added, start=1):
            if getattr(item, "id", None) is None:
                item.id = index

    async def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = len(self.added)


def _trial_user():
    return User(
        id=1,
        email="owner@example.test",
        hashed_password="unused",
        trial_ends_at=datetime.utcnow() + timedelta(days=1),
    )


def _get_json(app, path, session_responses):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = _trial_user

    async def override_session():
        yield _FakeSession(session_responses)

    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).get(path)
    finally:
        app.dependency_overrides.clear()
    return response


def _post_file(app, path, *, filename, content, media_type):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = _trial_user

    async def override_session():
        yield _FakeSession([])

    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).post(path, files={"file": (filename, content, media_type)})
    finally:
        app.dependency_overrides.clear()
    return response


class SummaryEndpointIntegrationTests(unittest.TestCase):
    def test_filecleaner_summary_returns_quality_totals(self):
        response = _get_json(file_app, "/files/summary", [[
            SimpleNamespace(status="complete", rows_original=100, rows_clean=70, duplicates_removed=20, empty_removed=5, whitespace_fixed=8),
            SimpleNamespace(status="error", rows_original=0, rows_clean=0, duplicates_removed=0, empty_removed=0, whitespace_fixed=0),
        ]])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["rows_saved"], 30)
        self.assertEqual(response.json()["quality_actions"], 33)

    def test_invoicefollow_summary_returns_cash_risk(self):
        response = _get_json(invoice_app, "/invoices/summary", [[
            SimpleNamespace(status="pending", amount=120.0, due_date=date(2026, 1, 1), cron_paused=False, payment_promise_date=None),
            SimpleNamespace(status="pending", amount=80.0, due_date=date(2026, 1, 1), cron_paused=True, payment_promise_date=date(2026, 6, 20)),
        ]])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pending_amount"], 200.0)
        self.assertEqual(response.json()["promised_amount"], 80.0)

    def test_pricetrackr_summary_returns_opportunity_metrics(self):
        response = _get_json(tracker_app, "/trackers/summary", [[
            SimpleNamespace(status="active", current_price=90.0, previous_price=100.0, min_price=80.0, in_stock=True),
            SimpleNamespace(status="active", current_price=140.0, previous_price=120.0, min_price=100.0, in_stock=False),
        ]])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["price_drop_count"], 1)
        self.assertEqual(response.json()["out_of_stock_count"], 1)

    def test_webhookmonitor_summary_returns_reliability_metrics(self):
        now = datetime.utcnow()
        response = _get_json(webhook_app, "/webhooks/summary", [
            [SimpleNamespace(id=10)],
            [
                SimpleNamespace(received_at=now, retry_count=0, last_retry_status=200, auto_retry_enabled=False),
                SimpleNamespace(received_at=now - timedelta(days=2), retry_count=2, last_retry_status=500, auto_retry_enabled=True),
            ],
        ])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_requests"], 2)
        self.assertEqual(response.json()["failed_forwards"], 1)

    def test_feedbacklens_weekly_summary_is_served_by_backend(self):
        response = _get_json(feedback_app, "/feedback/summary/weekly", [[
            SimpleNamespace(sentiment="positive", themes_json='["ux"]', is_urgent=False, created_at=datetime.utcnow()),
            SimpleNamespace(sentiment="negative", themes_json='["billing"]', is_urgent=True, created_at=datetime.utcnow()),
        ]])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 2)
        self.assertEqual(response.json()["urgent_count"], 1)
        self.assertIn("billing", response.json()["top_themes"])

    def test_filecleaner_utility_endpoint_returns_processed_download(self):
        source = Image.new("RGB", (80, 80), color=(130, 19, 70))
        raw = io.BytesIO()
        source.save(raw, format="PNG")

        response = _post_file(
            file_app,
            "/files/utility?output_format=webp&quality=70",
            filename="logo.png",
            content=raw.getvalue(),
            media_type="image/png",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/webp")
        self.assertIn("logo.cleaned.webp", response.headers["content-disposition"])
        converted = Image.open(io.BytesIO(response.content))
        self.assertEqual(converted.format, "WEBP")

    def test_invoicefollow_import_csv_creates_validated_invoices(self):
        content = (
            "client_name,client_email,amount,due_date\n"
            "Acme,billing@example.com,120.50,2026-07-01\n"
            "Globex,ap@globex.com,90,2026-07-15\n"
        ).encode("utf-8")

        response = _post_file(
            invoice_app,
            "/invoices/import-csv",
            filename="invoices.csv",
            content=content,
            media_type="text/csv",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["created"], 2)
        self.assertEqual(response.json()["invoices"][0]["client_email"], "billing@example.com")


if __name__ == "__main__":
    unittest.main()
