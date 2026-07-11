import sys
import asyncio
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

import apps.invoicefollow.backend.main as invoice_main
import backend_core.universal_main as universal_main
from backend_core.auth import User, get_current_user
from backend_core.database import get_session

TEST_ENCRYPTION_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="


class _FakeExecuteResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None

    def scalar_one(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class _FakeSession:
    def __init__(self, responses=None, item=None):
        self.responses = list(responses or [])
        self.item = item
        self.added = []
        self.committed = False
        self.executed = []

    async def execute(self, _query, _params=None):
        self.executed.append((_query, _params))
        if not self.responses:
            return _FakeExecuteResult([])
        response = self.responses.pop(0)
        if callable(response):
            response = response(_query)
        return _FakeExecuteResult(response)

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

    async def rollback(self):
        self.rolled_back = True

    async def delete(self, item):
        self.deleted = item


class _ManagedSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


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

    def test_gmail_oauth_returns_service_unavailable_when_credentials_are_missing(self):
        with patch.dict(invoice_main.os.environ, {"GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""}, clear=False):
            gmail = _client().post("/connect/gmail", json={"email": "owner@example.com"})

        self.assertEqual(gmail.status_code, 503)
        self.assertEqual(gmail.json()["detail"], "Google OAuth credentials are not configured.")

    def test_invoicefollow_requires_encryption_key_and_uses_timezone_aware_now(self):
        invoice_main.IntegrationsCrypto._fernet = None
        with patch.dict(invoice_main.os.environ, {"ENCRYPTION_KEY": ""}, clear=False):
            with self.assertRaises(RuntimeError):
                invoice_main.IntegrationsCrypto.get_fernet()

        now = invoice_main._utc_now()

        self.assertIsNotNone(now.tzinfo)
        self.assertEqual(now.utcoffset(), timezone.utc.utcoffset(None))

    def test_invoicefollow_persisted_timestamps_are_timezone_aware(self):
        timestamp_columns = (
            invoice_main.Invoice.__table__.c.created_at,
            invoice_main.Invoice.__table__.c.updated_at,
            invoice_main.Invoice.__table__.c.promise_expires_at,
            invoice_main.InvoiceReminderLog.__table__.c.sent_at,
            invoice_main.InvoiceReplyEvent.__table__.c.received_at,
            invoice_main.InvoicePaymentEvent.__table__.c.detected_at,
        )

        self.assertTrue(all(column.type.timezone for column in timestamp_columns))

    def test_invoice_settings_notifications_are_opt_in(self):
        settings = invoice_main.InvoiceSettings(user_id=1)

        self.assertFalse(settings.weekly_digest_enabled)
        self.assertFalse(settings.immediate_alerts_enabled)

    def test_public_rate_limit_uses_atomic_neon_counter(self):
        request = SimpleNamespace(
            headers={"x-forwarded-for": "203.0.113.9"},
            client=None,
        )
        allowed_session = _FakeSession(responses=[[1]])

        asyncio.run(invoice_main._rate_limit_public(request, "promise", allowed_session))

        statement = str(allowed_session.executed[0][0]).lower()
        self.assertIn("insert into invoice_public_rate_limits", statement)
        self.assertIn("on conflict", statement)
        self.assertIn("returning request_count", statement)
        self.assertTrue(allowed_session.committed)
        self.assertFalse(hasattr(invoice_main, "_PUBLIC_RATE_LIMITS"))

        blocked_session = _FakeSession(responses=[[]])
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(invoice_main._rate_limit_public(request, "promise", blocked_session))
        self.assertEqual(raised.exception.status_code, 429)

    def test_invoice_capacity_count_fails_closed_when_neon_is_unavailable(self):
        def fail_count(_query):
            raise RuntimeError("neon unavailable")

        session = _FakeSession(responses=[fail_count])

        with self.assertRaises(RuntimeError):
            asyncio.run(invoice_main._active_invoice_count(session, user_id=1))

    def test_cron_jobs_skip_when_neon_advisory_lock_is_already_held(self):
        session = _FakeSession(responses=[[False]])

        with patch.object(invoice_main, "get_managed_session", lambda: _ManagedSessionContext(session)):
            result = asyncio.run(invoice_main.poll_payment_providers())

        self.assertEqual(result["skipped_locked"], 1)
        statement = str(session.executed[0][0]).lower()
        self.assertIn("pg_try_advisory_lock", statement)
        self.assertIn("invoicefollow:payments", session.executed[0][1]["lock_name"])

    def test_import_acquires_neon_transaction_lock_before_counting_plan_capacity(self):
        session = _FakeSession(responses=[[], [4]])
        csv_payload = (
            b"client_name,client_email,amount,due_date\n"
            b"Acme,billing@acme.com,100,2026-08-01\n"
        )

        with patch.object(invoice_main, "_plan_for_user", return_value="free"):
            response = _client(session).post(
                "/invoices/import-csv",
                files={"file": ("invoices.csv", csv_payload, "text/csv")},
            )

        self.assertEqual(response.status_code, 200)
        statements = [str(query).lower() for query, _params in session.executed]
        self.assertIn("pg_advisory_xact_lock", statements[0])
        self.assertIn("count", statements[1])

    def test_reply_intent_caps_input_before_normalization_and_regex_matching(self):
        oversized = "x" * (invoice_main.MAX_REPLY_TEXT_CHARS + 10_000) + " we paid this invoice"

        normalized = invoice_main._normalize_intent_text(oversized)
        intent = invoice_main.classify_reply_intent(oversized)

        self.assertLessEqual(len(normalized), invoice_main.MAX_REPLY_TEXT_CHARS)
        self.assertEqual(intent["label"], "DESCONOCIDO")

    def test_mark_paid_methods_share_one_domain_helper(self):
        invoice = invoice_main.Invoice(
            id=10,
            user_id=1,
            client_name="Acme",
            client_email="billing@acme.test",
            amount=100,
            due_date=date.today(),
        )

        result = invoice_main._mark_invoice_paid(invoice)

        self.assertEqual(result["status"], "paid")
        self.assertEqual(invoice.status, "paid")
        self.assertTrue(invoice.cron_paused)
        self.assertIsNotNone(invoice.paid_at)

    def test_forward_address_tokens_are_nonempty_and_database_unique(self):
        constraints = {
            tuple(constraint.columns.keys())
            for constraint in invoice_main.InvoiceIntegrationSettings.__table__.constraints
            if type(constraint).__name__ == "UniqueConstraint"
        }
        first = invoice_main.InvoiceIntegrationSettings(user_id=1)
        second = invoice_main.InvoiceIntegrationSettings(user_id=2)

        self.assertIn(("forward_address_token",), constraints)
        self.assertGreaterEqual(len(first.forward_address_token), 32)
        self.assertNotEqual(first.forward_address_token, second.forward_address_token)

    def test_import_amount_accepts_common_international_formats(self):
        cases = {
            "1.234,56 EUR": 1234.56,
            "USD 1,234.56": 1234.56,
            "CHF 1'234.50": 1234.50,
            "1\u202f234,56": 1234.56,
            "S/ 1.234": 1234.0,
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(invoice_main._clean_import_amount(raw), expected)

    def test_template_preview_uses_explicit_non_persistent_object(self):
        preview = invoice_main._template_preview()

        self.assertIsInstance(preview, invoice_main.InvoiceTemplatePreview)
        self.assertNotIsInstance(preview, invoice_main.Invoice)
        self.assertEqual(preview.invoice_number, "#1042")

    def test_reminder_schedule_uses_logs_for_done_status(self):
        schedule = invoice_main.build_reminder_schedule(
            due_date=date(2026, 6, 1),
            today=date(2026, 7, 16),
            user_name="Victor",
            logs=[SimpleNamespace(template_key="friendly", status="sent")],
        )
        statuses = {item["tone"]: item["status"] for item in schedule}

        self.assertEqual(statuses["neutral"], "pending")
        self.assertEqual(statuses["friendly"], "done")
        self.assertEqual(statuses["firm"], "pending")

    def test_invoice_update_and_forward_detection_validate_corrupt_inputs(self):
        with self.assertRaises(Exception):
            invoice_main.InvoiceUpdate(amount=-10)
        with self.assertRaises(Exception):
            invoice_main.InvoiceUpdate(status="hacked")
        with self.assertRaises(Exception):
            invoice_main.InvoiceUpdate(currency="us dollar")
        with self.assertRaises(Exception):
            invoice_main.InvoiceEmailDetectRequest(
                sender_email="billing@example.test",
                source="forward",
                message_id="",
            )

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
            "/connect/stripe",
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
        invoice_main.IntegrationsCrypto._fernet = None
        try:
            with patch.dict(invoice_main.os.environ, {"ENCRYPTION_KEY": TEST_ENCRYPTION_KEY}, clear=False):
                response = _client(session).get(f"/connect/gmail/callback?code=CODE&state={state}")
                self.assertEqual(response.status_code, 200)
                self.assertTrue(integration.gmail_connected)
                self.assertEqual(invoice_main.decrypt_val(integration.gmail_access_token), "access-token")
                self.assertEqual(invoice_main.decrypt_val(integration.gmail_refresh_token), "refresh-token")
        finally:
            invoice_main.IntegrationsCrypto._fernet = None
            if original_exchange is not None:
                invoice_main.exchange_gmail_oauth_code = original_exchange

        self.assertEqual(integration.gmail_email, "owner@example.com")
        self.assertEqual(integration.gmail_state, "")

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

    def test_invoice_models_have_database_uniqueness_for_public_tokens_and_reply_events(self):
        invoice_constraints = {
            tuple(constraint.columns.keys())
            for constraint in invoice_main.Invoice.__table__.constraints
            if type(constraint).__name__ == "UniqueConstraint"
        }
        reply_constraints = {
            tuple(constraint.columns.keys())
            for constraint in invoice_main.InvoiceReplyEvent.__table__.constraints
            if type(constraint).__name__ == "UniqueConstraint"
        }

        self.assertIn(("promise_token",), invoice_constraints)
        self.assertIn(("user_id", "provider", "provider_message_id"), reply_constraints)

    def test_invoice_model_persists_public_promise_idempotency_fields(self):
        fields = getattr(invoice_main.Invoice, "model_fields", None) or getattr(invoice_main.Invoice, "__fields__", {})
        invoice = invoice_main.Invoice(
            user_id=1,
            client_name="Acme",
            client_email="billing@acme.test",
            amount=1200,
            due_date=date.today(),
        )
        days_until_expiry = (invoice.promise_expires_at - invoice.created_at).days

        self.assertIn("promise_used_at", fields)
        self.assertIn("promise_expires_at", fields)
        self.assertEqual(days_until_expiry, 30)

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
        session = _FakeSession(responses=[[1]])
        event = {"id": "evt_1", "type": "payment_intent.succeeded", "data": {"object": {"metadata": {}}}}
        with patch.dict(invoice_main.os.environ, {"STRIPE_WEBHOOK_SECRET": "whsec_test"}, clear=False):
            with patch.object(invoice_main.stripe.Webhook, "construct_event", return_value=event):
                response = _client(session).post(
                    "/invoices/webhooks/stripe",
                    json=event,
                    headers={"Stripe-Signature": "t=1,v1=test"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reason"], "missing_invoice_id")
        self.assertEqual(session.responses, [])

    def test_stripe_webhook_rejects_unsigned_payload_when_secret_missing(self):
        session = _FakeSession(responses=[[1]])
        with patch.dict(invoice_main.os.environ, {"STRIPE_WEBHOOK_SECRET": ""}, clear=False):
            response = _client(session).post(
                "/invoices/webhooks/stripe",
                json={"id": "evt_1", "type": "payment_intent.succeeded", "data": {"object": {"metadata": {}}}},
            )

        self.assertEqual(response.status_code, 500)

    def test_stripe_webhook_rejects_missing_signature_when_secret_is_configured(self):
        session = _FakeSession(responses=[[1]])
        with patch.dict(invoice_main.os.environ, {"STRIPE_WEBHOOK_SECRET": "whsec_test"}, clear=False):
            response = _client(session).post(
                "/invoices/webhooks/stripe",
                json={"id": "evt_1", "type": "payment_intent.succeeded", "data": {"object": {"metadata": {}}}},
            )

        self.assertEqual(response.status_code, 400)

    def test_stripe_webhook_rejects_invalid_signature(self):
        session = _FakeSession(responses=[[1]])
        with patch.dict(invoice_main.os.environ, {"STRIPE_WEBHOOK_SECRET": "whsec_test"}, clear=False):
            with patch.object(invoice_main.stripe.Webhook, "construct_event", side_effect=ValueError("bad signature")):
                response = _client(session).post(
                    "/invoices/webhooks/stripe",
                    json={"id": "evt_1", "type": "payment_intent.succeeded", "data": {"object": {"metadata": {}}}},
                    headers={"Stripe-Signature": "t=1,v1=bad"},
                )

        self.assertEqual(response.status_code, 400)

    def test_public_promise_is_idempotent_once_used(self):
        invoice = invoice_main.Invoice(
            id=10,
            user_id=1,
            client_name="Acme",
            client_email="billing@acme.test",
            amount=1200,
            due_date=date.today() - timedelta(days=3),
            promise_token="promise-token",
        )
        session = _FakeSession(responses=[[1], [invoice], [1], [invoice]])
        client = _client(session)

        first = client.get("/invoices/promise/promise-token")
        second = client.get("/invoices/promise/promise-token")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["message"], "Payment promise already saved.")
        self.assertIsNotNone(invoice.promise_used_at)

    def test_public_promise_rejects_expired_token(self):
        invoice = invoice_main.Invoice(
            id=10,
            user_id=1,
            client_name="Acme",
            client_email="billing@acme.test",
            amount=1200,
            due_date=date.today() - timedelta(days=3),
            promise_token="expired-token",
            promise_expires_at=invoice_main._utc_now() - timedelta(minutes=1),
        )
        session = _FakeSession(responses=[[1], [invoice]])

        response = _client(session).get("/invoices/promise/expired-token")

        self.assertEqual(response.status_code, 404)

    def test_sender_company_falls_back_to_unknown_when_sender_is_blank(self):
        self.assertEqual(invoice_main._sender_company("", ""), "Unknown")

    def test_is_time_to_send_fails_safe_for_invalid_send_window(self):
        settings = invoice_main.InvoiceSettings(user_id=1, send_hour=18, no_send_after_hour=9, skip_weekends=False)

        self.assertFalse(invoice_main.is_time_to_send(settings, datetime(2026, 7, 8, 18, 30)))

    def test_invoicefollow_exposes_stripe_but_not_paypal(self):
        route_paths = {getattr(route, "path", "") for route in invoice_main.app.routes}
        backend = (ROOT / "apps" / "invoicefollow" / "backend" / "main.py").read_text(encoding="utf-8").lower()

        self.assertIn("/connect/stripe", route_paths)
        self.assertNotIn("/connect/paypal", route_paths)
        self.assertNotIn("paypal", backend)

    def test_stripe_event_polling_pages_with_starting_after(self):
        calls = []

        class FakeResponse:
            status_code = 200

            def __init__(self, payload):
                self.payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self.payload

        class FakeClient:
            def __init__(self, *args, **kwargs):
                self.responses = [
                    FakeResponse({"data": [{"id": "evt_1"}, {"id": "evt_2"}], "has_more": True}),
                    FakeResponse({"data": [{"id": "evt_3"}], "has_more": False}),
                ]

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, _url, **kwargs):
                calls.append(kwargs["params"].copy())
                return self.responses.pop(0)

        with patch.object(invoice_main, "decrypt_val", return_value="rk_test"), \
             patch.object(invoice_main.httpx, "AsyncClient", FakeClient):
            events = asyncio.run(invoice_main.list_stripe_payment_events("encrypted"))

        self.assertEqual([event["id"] for event in events], ["evt_1", "evt_2", "evt_3"])
        self.assertNotIn("starting_after", calls[0])
        self.assertEqual(calls[1]["starting_after"], "evt_2")

    def test_gmail_message_details_use_bounded_concurrency(self):
        class FakeResponse:
            def __init__(self, message_id):
                self.message_id = message_id

            def raise_for_status(self):
                return None

            def json(self):
                return {"id": self.message_id, "payload": {"headers": []}}

        class FakeClient:
            def __init__(self):
                self.active = 0
                self.max_active = 0

            async def get(self, url, **_kwargs):
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                await asyncio.sleep(0.001)
                self.active -= 1
                return FakeResponse(url.rsplit("/", 1)[-1])

        async def fetch():
            client = FakeClient()
            messages = await invoice_main._fetch_gmail_message_details(
                client,
                [{"id": f"m-{index}"} for index in range(25)],
                {"Authorization": "Bearer token"},
            )
            return client, messages

        client, messages = asyncio.run(fetch())

        self.assertEqual(len(messages), 25)
        self.assertGreater(client.max_active, 1)
        self.assertLessEqual(client.max_active, invoice_main.GMAIL_DETAIL_CONCURRENCY)

    def test_reply_poll_records_automated_action_audit(self):
        invoice = invoice_main.Invoice(
            id=7,
            user_id=1,
            client_name="Acme",
            client_email="billing@acme.test",
            amount=100,
            due_date=date.today() - timedelta(days=3),
        )
        integration = invoice_main.InvoiceIntegrationSettings(user_id=1, gmail_connected=True)
        session = _FakeSession(responses=[[True], [invoice], [integration], [], []])

        async def fake_replies(*_args, **_kwargs):
            return [{"id": "gmail-1", "provider": "gmail", "text": "payment is processing"}]

        with patch.object(invoice_main, "get_managed_session", lambda: _ManagedSessionContext(session)), \
             patch.object(invoice_main, "fetch_gmail_thread_replies", fake_replies):
            result = asyncio.run(invoice_main.poll_reply_threads())

        audits = [item for item in session.added if isinstance(item, invoice_main.InvoiceAuditLog)]
        self.assertEqual(result["processed_replies"], 1)
        self.assertEqual(len(audits), 1)
        self.assertEqual(audits[0].actor_type, "system")
        self.assertEqual(audits[0].action, "pause_7_days")
        self.assertEqual(audits[0].source_event_id, "gmail-1")

    def test_settings_update_records_authenticated_actor(self):
        settings = invoice_main.InvoiceSettings(user_id=1, company_name="Before")
        integration = invoice_main.InvoiceIntegrationSettings(user_id=1)
        session = _FakeSession(responses=[[settings], [settings], [integration]])

        response = _client(session).put("/settings", json={"company_name": "After"})

        audits = [item for item in session.added if isinstance(item, invoice_main.InvoiceAuditLog)]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(audits), 1)
        self.assertEqual(audits[0].actor_user_id, 1)
        self.assertEqual(audits[0].action, "settings_updated")
        self.assertIn("company_name", audits[0].details_json)

    def test_invoice_export_reads_neon_in_bounded_pages(self):
        first = invoice_main.Invoice(
            id=2,
            user_id=1,
            client_name="Acme",
            client_email="billing@acme.test",
            amount=100,
            due_date=date.today(),
        )
        second = invoice_main.Invoice(
            id=1,
            user_id=1,
            client_name="Beta",
            client_email="billing@beta.test",
            amount=200,
            due_date=date.today(),
        )
        session = _FakeSession(responses=[[first], [second], []])

        async def collect_rows():
            return [
                row
                async for row in invoice_main._iter_invoice_export_rows(
                    session,
                    user_id=1,
                    page_size=1,
                )
            ]

        rows = asyncio.run(collect_rows())

        self.assertEqual([row["id"] for row in rows], [2, 1])
        statements = [str(query).lower() for query, _params in session.executed]
        self.assertTrue(all("limit" in statement for statement in statements))
        self.assertIn("invoices.id <", statements[1])

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

    def test_payment_poll_counts_matched_payments_not_scanned_provider_events(self):
        invoice = invoice_main.Invoice(
            id=7,
            user_id=1,
            client_name="Acme",
            client_email="billing@acme.test",
            amount=100,
            due_date=date.today() - timedelta(days=10),
            status="overdue",
        )
        integration = invoice_main.InvoiceIntegrationSettings(user_id=1, stripe_connected=True, stripe_api_key="sk_test")
        session = _FakeSession(responses=[
            [True],
            [invoice],
            [integration],
            [],
            [],
        ])

        async def fake_events(_api_key):
            return [
                {"id": "evt_unmatched", "type": "payment_intent.succeeded", "data": {"object": {"amount_received": 100, "currency": "usd", "metadata": {"invoice_id": "999"}}}},
                {"id": "evt_matched", "type": "payment_intent.succeeded", "data": {"object": {"amount_received": 10000, "currency": "usd", "metadata": {"invoice_id": "7"}}}},
            ]

        with patch.object(invoice_main, "get_managed_session", lambda: _ManagedSessionContext(session)), \
             patch.object(invoice_main, "list_stripe_payment_events", fake_events):
            result = asyncio.run(invoice_main.poll_payment_providers())

        self.assertEqual(result["processed_payments"], 1)
        self.assertEqual(result["matched_payments"], 1)

    def test_overdue_reminder_enqueue_enforces_per_user_per_minute_guard(self):
        today = date.today()
        invoice = invoice_main.Invoice(
            id=1,
            user_id=1,
            client_name="Acme",
            client_email="billing@acme.test",
            amount=100,
            due_date=today - timedelta(days=8),
            status="overdue",
        )
        user = _trial_user()
        settings = invoice_main.InvoiceSettings(user_id=1, skip_weekends=False, send_hour=0, no_send_after_hour=23)
        session = _FakeSession(responses=[
            [True],
            [],
            [],
            [invoice],
            [settings],
            [user],
            [0],
            lambda query: [10] if "count" in str(query).lower() else [],
            [],
            [],
        ])

        with patch.object(invoice_main, "get_managed_session", lambda: _ManagedSessionContext(session)), \
             patch.object(invoice_main, "_plan_for_user", return_value="pro"):
            asyncio.run(invoice_main.enqueue_overdue_reminders())

        jobs = [item for item in session.added if type(item).__name__ == "SystemOutbox"]
        logs = [item for item in session.added if isinstance(item, invoice_main.InvoiceReminderLog)]
        self.assertEqual(jobs, [])
        self.assertEqual(logs, [])

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
