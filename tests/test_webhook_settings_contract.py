import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

from fastapi.testclient import TestClient

import apps.webhookmonitor.backend.main as webhook_main
from apps.webhookmonitor.backend.main import WebhookSettings
from backend_core.auth import User, get_current_user
from backend_core.database import get_session


class _FakeExecuteResult:
    def __init__(self, rows=None):
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class _SettingsSession:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []
        self.flushed = False
        self.queries = []

    async def execute(self, query):
        self.queries.append(str(query))
        return _FakeExecuteResult([self.existing] if self.existing else [])

    def add(self, item):
        self.added.append(item)
        self.existing = item

    async def flush(self):
        self.flushed = True


def _trial_user():
    return User(
        id=42,
        email="owner@example.test",
        hashed_password="unused",
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=1),
    )


class WebhookSettingsContractTests(unittest.TestCase):
    def tearDown(self):
        webhook_main.app.dependency_overrides.clear()

    def _put_settings(self, session, payload):
        webhook_main.app.dependency_overrides.clear()
        webhook_main.app.dependency_overrides[get_current_user] = _trial_user

        async def override_session():
            yield session

        webhook_main.app.dependency_overrides[get_session] = override_session

        try:
            return TestClient(webhook_main.app).put("/settings/webhook-prefs", json=payload)
        finally:
            webhook_main.app.dependency_overrides.clear()

    def test_webhook_settings_put_updates_frontend_contract(self):
        session = _SettingsSession()

        response = self._put_settings(
            session,
            {
                "forward_url": "https://example.com/webhooks",
                "expected_interval_minutes": 15,
                "alert_email": "alerts@example.test",
                "auto_retry_enabled": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        self.assertTrue(session.flushed)
        saved = session.added[-1]
        self.assertIsInstance(saved, WebhookSettings)
        self.assertEqual(saved.user_id, 42)
        self.assertEqual(saved.forward_url, "https://example.com/webhooks")
        self.assertEqual(saved.expected_interval_minutes, 15)
        self.assertEqual(saved.alert_email, "alerts@example.test")
        self.assertTrue(saved.auto_retry_enabled)

    def test_webhook_settings_put_rejects_private_forward_url(self):
        response = self._put_settings(
            _SettingsSession(),
            {
                "forward_url": "http://127.0.0.1:8000/hook",
                "expected_interval_minutes": 0,
                "alert_email": "",
                "auto_retry_enabled": False,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("public http(s) URL", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
