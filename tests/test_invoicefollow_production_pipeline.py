import sys
import asyncio
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

import apps.invoicefollow.backend.main as invoice_main
import backend_core.universal_main as universal_main
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

    def fetchall(self):
        return self.rows


class _FakeSession:
    def __init__(self, responses=None, item=None):
        self.responses = list(responses or [])
        self.item = item
        self.added = []
        self.committed = False

    async def execute(self, _query, _params=None):
        if not self.responses:
            return _FakeExecuteResult([])
        return _FakeExecuteResult(self.responses.pop(0))

    async def get(self, _model, _item_id):
        return self.item

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        for index, item in enumerate(self.added, start=1):
            fields = getattr(type(item), "model_fields", None)
            if fields is None:
                fields = getattr(type(item), "__fields__", {})
            if "id" in fields and getattr(item, "id", None) is None:
                item.id = index

    async def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = 1

    async def commit(self):
        self.committed = True

    async def delete(self, item):
        self.deleted = item


def _trial_user():
    return User(
        id=1,
        email="owner@example.test",
        hashed_password="unused",
        trial_ends_at=datetime.utcnow() + timedelta(days=1),
    )


def _client(session=None):
    invoice_main.app.dependency_overrides.clear()
    invoice_main.app.dependency_overrides[get_current_user] = _trial_user

    async def override_session():
        yield session or _FakeSession()

    invoice_main.app.dependency_overrides[get_session] = override_session
    return TestClient(invoice_main.app)


class InvoiceFollowProductionPipelineTests(unittest.TestCase):
    def tearDown(self):
        invoice_main.app.dependency_overrides.clear()
        universal_main.app.dependency_overrides.clear()

    def test_manual_form_creates_tracking_record_without_issuing_legal_invoice(self):
        response = _client().post(
            "/invoices",
            json={
                "client_name": "Acme",
                "client_email": "billing@acme.com",
                "amount": 1200,
                "currency": "USD",
                "due_date": "2026-07-15",
                "invoice_number": "INV-1042",
                "issued_date": "2026-07-01",
                "notes": "Invoice was sent by WhatsApp.",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "manual_form")
        self.assertEqual(payload["currency"], "USD")
        self.assertEqual(payload["invoice_number"], "INV-1042")
        self.assertFalse(payload["creates_legal_invoice"])

    def test_ai_tone_route_and_frontend_surface_are_removed(self):
        route_paths = {getattr(route, "path", "") for route in invoice_main.app.routes}
        dashboard = (ROOT / "apps" / "invoicefollow" / "frontend" / "src" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")

        self.assertNotIn("/invoices/{invoice_id}/ai-tone", route_paths)
        self.assertNotIn("ai-tone", dashboard)
        self.assertNotIn("AI Tone", dashboard)
        self.assertNotIn("Write follow-up", dashboard)

    def test_frontend_promotes_tracking_records_not_invoice_generation(self):
        dashboard = (ROOT / "apps" / "invoicefollow" / "frontend" / "src" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
        landing = (ROOT / "apps" / "invoicefollow" / "frontend" / "src" / "app" / "page.tsx").read_text(encoding="utf-8")

        for text in (dashboard, landing):
            self.assertNotIn("Create invoices manually", text)
            self.assertNotIn("Add one invoice manually", text)
            self.assertNotIn("Generate invoice", text)
            self.assertNotIn("Issue invoice", text)
        self.assertIn("Import existing invoice records", dashboard)
        self.assertIn("Track existing invoices", landing)

    def test_detects_existing_invoice_from_email_without_creating_legal_document(self):
        parsed = invoice_main.parse_invoice_email(
            subject="Factura INV-1042 payment due",
            body=(
                "Client: Acme Corp\n"
                "Invoice #INV-1042\n"
                "Amount due: $1,240.50\n"
                "Issued: June 1, 2026\n"
                "Due date: 2026-07-15\n"
                "Please pay via the usual bank transfer."
            ),
            sender_email="billing@acme.test",
            sender_name="Acme Billing",
        )
        missed = invoice_main.parse_invoice_email(
            subject="Project notes",
            body="No payable document here.",
            sender_email="hello@acme.test",
            sender_name="Acme",
        )

        self.assertEqual(parsed["status"], "detected")
        self.assertEqual(parsed["invoice_number"], "INV-1042")
        self.assertEqual(parsed["client_name"], "Acme Corp")
        self.assertEqual(parsed["client_email"], "billing@acme.test")
        self.assertEqual(parsed["amount"], 1240.50)
        self.assertEqual(parsed["currency"], "USD")
        self.assertEqual(parsed["due_date"], "2026-07-15")
        self.assertEqual(parsed["issued_date"], "2026-06-01")
        self.assertFalse(parsed["creates_invoice_document"])
        self.assertEqual(missed["status"], "not_detected")
        self.assertIn("forward an existing invoice email", missed["next_step"])

    def test_detect_email_handles_amount_with_comma_and_textual_due_date(self):
        parsed = invoice_main.parse_invoice_email(
            subject="Invoice #INV-2041 from Clara Studio",
            body="Hi, attached is invoice INV-2041 for $2,400 due July 31, 2026.",
            sender_email="billing@clarastudio.com",
            sender_name="Clara Studio Billing",
        )

        self.assertEqual(parsed["status"], "detected")
        self.assertEqual(parsed["client_name"], "Clara Studio")
        self.assertEqual(parsed["invoice_number"], "INV-2041")
        self.assertEqual(parsed["amount"], 2400.0)
        self.assertEqual(parsed["currency"], "USD")
        self.assertEqual(parsed["due_date"], "2026-07-31")
        self.assertGreaterEqual(parsed["confidence"], 0.75)

    def test_digest_has_invoicefollow_alias_to_avoid_universal_route_collision(self):
        route_paths = {getattr(route, "path", "") for route in invoice_main.app.routes}
        dashboard = (ROOT / "apps" / "invoicefollow" / "frontend" / "src" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")

        self.assertIn("/invoicefollow/digest", route_paths)
        self.assertIn('apiClient.get<DigestSummary>("/invoicefollow/digest")', dashboard)

    def test_oauth_connectors_return_service_unavailable_when_client_ids_are_missing(self):
        with patch.dict(invoice_main.os.environ, {"GOOGLE_CLIENT_ID": "", "MICROSOFT_CLIENT_ID": ""}, clear=False):
            gmail = _client().post("/connect/gmail", json={"email": "owner@example.com"})
            outlook = _client().post("/connect/outlook", json={"email": "owner@example.com"})

        self.assertEqual(gmail.status_code, 503)
        self.assertEqual(outlook.status_code, 503)
        self.assertEqual(gmail.json()["detail"], "Google OAuth credentials are not configured.")
        self.assertEqual(outlook.json()["detail"], "Microsoft OAuth credentials are not configured.")

    def test_schedule_and_templates_are_fixed_not_ai_generated(self):
        schedule = invoice_main.build_reminder_schedule(
            due_date=date(2026, 6, 1),
            today=date(2026, 7, 16),
            user_name="Victor",
        )
        invoice = invoice_main.Invoice(
            id=42,
            user_id=1,
            client_name="Acme",
            client_email="billing@acme.test",
            amount=1200,
            currency="USD",
            due_date=date(2026, 6, 1),
            invoice_number="INV-1042",
        )

        subject, html_body, metadata = invoice_main.render_reminder_template(
            invoice,
            stage_day=30,
            company_name="DevForge",
            user_name="Victor",
            today=date(2026, 7, 16),
        )

        self.assertEqual([stage["day"] for stage in schedule], [0, 7, 15, 30, 45])
        self.assertEqual(schedule[2]["sender_label"], "Victor (Billing)")
        self.assertEqual(schedule[3]["sender_label"], "Victor (Accounts Receivable)")
        self.assertEqual(metadata["stage_day"], 30)
        self.assertIn("INV-1042", subject)
        self.assertNotIn("PDF", html_body.upper())
        self.assertNotIn("Gemini", html_body)
        self.assertNotIn("AI", html_body)

    def test_reply_intent_paid_without_payment_confirmation_pauses_for_verification(self):
        invoice = invoice_main.Invoice(
            id=7,
            user_id=1,
            client_name="Acme",
            client_email="billing@acme.test",
            amount=1200,
            due_date=date(2026, 6, 1),
        )

        intent = invoice_main.classify_reply_intent("We paid this invoice this morning, please check.")
        action = invoice_main.apply_reply_intent(
            invoice,
            intent,
            payment_confirmed=False,
            today=date(2026, 6, 22),
        )

        self.assertEqual(intent["label"], "PAGADO")
        self.assertEqual(action["action"], "pause_verify_payment")
        self.assertEqual(invoice.status, "pending")
        self.assertTrue(invoice.cron_paused)
        self.assertIn("verify payment", invoice.manual_review_reason)

    def test_reply_intent_negation_and_ambiguous_context_go_to_manual_review_without_ai(self):
        negated = invoice_main.classify_reply_intent("No transferi nada todavia.")
        ambiguous = invoice_main.classify_reply_intent("El banco me dijo que la transferi.")

        self.assertEqual(negated["label"], "DESCONOCIDO")
        self.assertEqual(negated["engine"], "deterministic")
        self.assertTrue(negated["manual_review_required"])
        self.assertEqual(ambiguous["label"], "DESCONOCIDO")
        self.assertEqual(ambiguous["engine"], "deterministic")
        self.assertTrue(ambiguous["manual_review_required"])

    def test_stripe_metadata_matches_exact_invoice_id(self):
        invoice = invoice_main.Invoice(
            id=42,
            user_id=1,
            client_name="Acme",
            client_email="billing@acme.test",
            amount=1200,
            due_date=date(2026, 6, 1),
        )
        event = {
            "id": "evt_123",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_123",
                    "amount_received": 120000,
                    "currency": "usd",
                    "metadata": {"invoice_id": "42"},
                }
            },
        }

        result = invoice_main.detect_stripe_payment_for_invoice(event, invoice)

        self.assertTrue(result["matched"])
        self.assertEqual(result["provider_event_id"], "evt_123")
        self.assertEqual(result["amount"], 1200.0)

    def test_weekly_digest_groups_payments_excuses_reminders_and_risk(self):
        today = date(2026, 6, 22)
        digest = invoice_main.build_weekly_digest(
            invoices=[
                SimpleNamespace(
                    id=1,
                    status="paid",
                    amount=1200,
                    due_date=date(2026, 5, 1),
                    paid_at=datetime(2026, 6, 20, 12, 0),
                    payment_promise_date=None,
                    reminders_sent=2,
                ),
                SimpleNamespace(
                    id=2,
                    status="pending",
                    amount=3000,
                    due_date=date(2026, 5, 1),
                    paid_at=None,
                    payment_promise_date=date(2026, 6, 19),
                    reminders_sent=4,
                ),
                SimpleNamespace(
                    id=3,
                    status="pending",
                    amount=900,
                    due_date=date(2026, 6, 15),
                    paid_at=None,
                    payment_promise_date=None,
                    reminders_sent=1,
                ),
            ],
            reminder_logs=[
                SimpleNamespace(sent_at=datetime(2026, 6, 16, 9, 0), status="sent"),
                SimpleNamespace(sent_at=datetime(2026, 6, 18, 9, 0), status="sent"),
            ],
            payment_events=[
                SimpleNamespace(detected_at=datetime(2026, 6, 20, 12, 0), amount=1200, status="succeeded"),
            ],
            today=today,
        )

        self.assertEqual(digest["payments_detected_this_week"], 1)
        self.assertEqual(digest["valid_excuses_pending"], 1)
        self.assertEqual(digest["reminders_sent"], 2)
        self.assertEqual(digest["invoices_at_risk"], 1)
        self.assertEqual(digest["month_summary"]["recovered_amount"], 1200)

    def test_metrics_ignore_unreasonable_issued_date_for_average_payment_time(self):
        paid_invoice = invoice_main.Invoice(
            id=20,
            user_id=1,
            client_name="Victor",
            client_email="victor@example.test",
            amount=10,
            currency="PEN",
            due_date=date(2026, 10, 3),
            issued_date=date(2005, 11, 2),
            status="paid",
            cron_paused=True,
            paid_at=datetime(2026, 7, 4, 12, 0),
            created_at=datetime(2026, 7, 4, 9, 0),
        )

        response = _client(_FakeSession(responses=[[paid_invoice]])).get("/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["avg_payment_time_days"], 0)

    def test_contract_endpoints_and_frontend_markdown_are_present(self):
        route_paths = {getattr(route, "path", "") for route in invoice_main.app.routes}
        expected_paths = {
            "/invoices",
            "/invoices/{invoice_id}",
            "/invoices/{invoice_id}/timeline",
            "/invoices/{invoice_id}/pause",
            "/invoices/{invoice_id}/resume",
            "/invoices/{invoice_id}/mark-paid",
            "/invoices/detect-email",
            "/invoices/drafts/{draft_id}/confirm",
            "/templates",
            "/templates/{template_id}",
            "/connect/gmail",
            "/connect/gmail/callback",
            "/connect/outlook",
            "/connect/outlook/callback",
            "/connect/stripe",
            "/connect/paypal",
            "/metrics",
            "/digest",
            "/settings",
        }
        contract = ROOT / "docs" / "features" / "invoicefollow-frontend-contract.md"

        self.assertTrue(expected_paths.issubset(route_paths))
        self.assertTrue(contract.exists())
        content = contract.read_text(encoding="utf-8")
        self.assertIn("Manual form tracks existing invoices only", content)
        self.assertIn("AI is not part of InvoiceFollow", content)
        self.assertIn("/invoices/detect-email", content)
        self.assertIn("/connect/gmail", content)
        self.assertIn("/connect/stripe", content)

    def test_gmail_oauth_start_does_not_mark_connected_until_callback(self):
        backend = (ROOT / "apps" / "invoicefollow" / "backend" / "main.py").read_text(encoding="utf-8")
        session = _FakeSession()
        with patch.dict(invoice_main.os.environ, {"GOOGLE_CLIENT_ID": "google-client-id", "GOOGLE_CLIENT_SECRET": "google-client-secret"}, clear=False):
            response = _client(session).post("/connect/gmail", json={"email": "owner@example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["connected"])
        integration = next(item for item in session.added if isinstance(item, invoice_main.InvoiceIntegrationSettings))
        self.assertFalse(integration.gmail_connected)
        self.assertEqual(integration.gmail_email, "owner@example.com")
        self.assertNotIn("https://api.devforgeapp.pro", backend)
        self.assertNotIn("https://api.devforgeapp.pro", response.json()["oauth_url"])

    def test_gmail_oauth_callback_exchanges_code_and_stores_tokens(self):
        state = invoice_main._make_oauth_state()
        integration = invoice_main.InvoiceIntegrationSettings(user_id=1, gmail_state=state)
        session = _FakeSession(responses=[[integration]])
        original_exchange = getattr(invoice_main, "exchange_gmail_oauth_code", None)

        async def fake_exchange(code, redirect_uri):
            return {
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "expires_in": 3600,
                "email": "owner@example.com",
            }

        invoice_main.exchange_gmail_oauth_code = fake_exchange
        try:
            response = _client(session).get(f"/connect/gmail/callback?code=CODE&state={state}")
        finally:
            if original_exchange is not None:
                invoice_main.exchange_gmail_oauth_code = original_exchange

        self.assertEqual(response.status_code, 200)
        self.assertTrue(integration.gmail_connected)
        self.assertEqual(invoice_main.decrypt_val(integration.gmail_access_token), "access-token")
        self.assertEqual(invoice_main.decrypt_val(integration.gmail_refresh_token), "refresh-token")
        self.assertEqual(integration.gmail_email, "owner@example.com")

    def test_oauth_callback_rejects_expired_state(self):
        expired_state = f"token:{int(invoice_main._utc_now().timestamp()) - 601}"
        integration = invoice_main.InvoiceIntegrationSettings(user_id=1, gmail_state=expired_state)
        session = _FakeSession(responses=[[integration]])

        response = _client(session).get(f"/connect/gmail/callback?code=CODE&state={expired_state}")

        self.assertEqual(response.status_code, 400)

    def test_create_invoice_uses_high_entropy_promise_token(self):
        session = _FakeSession()
        response = _client(session).post(
            "/invoices",
            json={
                "client_name": "Acme",
                "client_email": "billing@acme.com",
                "amount": 1200,
                "currency": "USD",
                "due_date": "2026-07-15",
            },
        )

        self.assertEqual(response.status_code, 200)
        invoice = next(item for item in session.added if isinstance(item, invoice_main.Invoice))
        self.assertGreaterEqual(len(invoice.promise_token), 32)

    def test_weekly_digest_ignores_undated_events(self):
        digest = invoice_main.build_weekly_digest(
            invoices=[],
            reminder_logs=[SimpleNamespace(status="sent", sent_at=None)],
            payment_events=[SimpleNamespace(status="succeeded", detected_at=None)],
            today=date(2026, 7, 6),
        )

        self.assertEqual(digest["payments_detected_this_week"], 0)
        self.assertEqual(digest["reminders_sent"], 0)
        self.assertEqual(digest["month_summary"]["invoices_sent"], 0)

    def test_stripe_webhook_ignores_missing_invoice_id_without_scanning_invoices(self):
        session = _FakeSession(responses=[])
        response = _client(session).post(
            "/invoices/webhooks/stripe",
            json={"id": "evt_1", "type": "payment_intent.succeeded", "data": {"object": {"metadata": {}}}},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reason"], "missing_invoice_id")
        self.assertEqual(session.responses, [])

    def test_reply_and_payment_crons_call_real_pollers(self):
        calls = []
        original_replies = invoice_main.poll_reply_threads
        original_payments = invoice_main.poll_payment_providers

        async def fake_replies():
            calls.append("replies")
            return {"processed_replies": 2, "paused_invoices": 1}

        async def fake_payments():
            calls.append("payments")
            return {"processed_payments": 3, "matched_payments": 2}

        import os
        old_secret = os.environ.get("CRON_SECRET")
        os.environ["CRON_SECRET"] = "cron-test-secret"
        invoice_main.poll_reply_threads = fake_replies
        invoice_main.poll_payment_providers = fake_payments
        try:
            client = _client()
            replies = client.post("/invoices/cron/replies/poll?sync=true", headers={"Authorization": "Bearer cron-test-secret"})
            payments = client.post("/invoices/cron/payments/poll?sync=true", headers={"Authorization": "Bearer cron-test-secret"})
        finally:
            invoice_main.poll_reply_threads = original_replies
            invoice_main.poll_payment_providers = original_payments
            if old_secret is None:
                os.environ.pop("CRON_SECRET", None)
            else:
                os.environ["CRON_SECRET"] = old_secret

        self.assertEqual(replies.status_code, 200)
        self.assertEqual(payments.status_code, 200)
        self.assertEqual(replies.json()["processed_replies"], 2)
        self.assertEqual(payments.json()["processed_payments"], 3)
        self.assertEqual(calls, ["replies", "payments"])

    def test_send_email_worker_raises_when_provider_fails_so_outbox_retries(self):
        original_send = invoice_main.send_email
        invoice_main.send_email = lambda **_kwargs: False
        try:
            with self.assertRaises(RuntimeError):
                asyncio.run(invoice_main.handle_send_email({"to": "client@example.test", "subject": "Invoice", "html_body": "<p>Pay</p>"}))
        finally:
            invoice_main.send_email = original_send

    def test_plan_limits_and_cli_match_pricing_spec(self):
        limits = invoice_main.INVOICEFOLLOW_LIMITS
        cli = (ROOT / "apps" / "invoicefollow" / "cli" / "invoicefollow.py").read_text(encoding="utf-8")

        self.assertEqual(limits["free"].max_active_invoices, 5)
        self.assertEqual(limits["free"].monthly_emails, 25)
        self.assertFalse(limits["free"].payment_connections_enabled)
        self.assertFalse(limits["free"].weekly_digest_enabled)
        self.assertEqual(limits["pro"].max_active_invoices, 50)
        self.assertEqual(limits["team"].max_active_invoices, 200)
        for phrase in [
            "invoicefollow login --api-key KEY",
            "invoices list --status pending",
            "invoices create",
            "--currency",
            "templates list",
            "templates edit",
        ]:
            self.assertIn(phrase, cli)

    def test_invoicefollow_routes_are_live_on_universal_backend(self):
        universal_main.app.dependency_overrides.clear()
        universal_main.app.dependency_overrides[get_current_user] = _trial_user

        async def override_session():
            yield _FakeSession()

        universal_main.app.dependency_overrides[get_session] = override_session
        client = TestClient(universal_main.app)

        for method, path in [
            ("GET", "/invoices"),
            ("GET", "/templates"),
            ("GET", "/metrics"),
            ("GET", "/digest"),
        ]:
            with self.subTest(path=path):
                response = client.request(method, path)
                self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
