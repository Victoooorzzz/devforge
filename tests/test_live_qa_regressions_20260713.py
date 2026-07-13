import asyncio
import sys
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

import apps.filecleaner.backend.main as filecleaner
import apps.invoicefollow.backend.main as invoicefollow


class FileCleanerLiveQaRegressionTests(unittest.TestCase):
    def test_text_dtype_detection_uses_pandas_compatibility_helpers(self):
        self.assertTrue(filecleaner._is_text_series(filecleaner.pd.Series(["a"], dtype="object")))
        self.assertTrue(filecleaner._is_text_series(filecleaner.pd.Series(["a"], dtype="string")))

    def test_deep_clean_collapses_internal_whitespace_and_uses_row_country_for_phones(self):
        df = filecleaner.pd.DataFrame(
            {
                "name": ["John   Doe", "John Doe"],
                "country": ["Peru", "Peru"],
                "phone": ["987 654 321", "+51 987654321"],
            }
        )

        engine = filecleaner.DeepCleanEngine(df)
        cleaned = engine.clean()

        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned.iloc[0]["name"], "John Doe")
        self.assertEqual(cleaned.iloc[0]["phone"], "+51987654321")

    def test_local_ai_analysis_reports_whitespace_and_invalid_business_values(self):
        content = (
            "name,email,amount,due_date\n"
            " John   Doe ,john@example.com,abc,not-a-date\n"
            "John Doe,john@example.com,100,2026-07-13\n"
        ).encode("utf-8")

        result = filecleaner._analyze_file_locally(content, "qa.csv")
        issues = " ".join(item["issue"] for item in result["suggestions"])

        self.assertIn("whitespace", issues.lower())
        self.assertIn("invalid business values", issues.lower())

    def test_fuzzy_endpoint_requires_identity_compatibility(self):
        source = (ROOT / "apps" / "filecleaner" / "backend" / "main.py").read_text(encoding="utf-8")

        self.assertIn("_rows_identity_compatible", source)
        self.assertIn("_rows_identity_compatible(df.iloc[i], df.iloc[j], thresh)", source)


class DashboardLiveQaRegressionTests(unittest.TestCase):
    def test_webhook_search_clear_and_invalid_json_have_explicit_safe_contracts(self):
        page = (ROOT / "apps" / "webhookmonitor" / "frontend" / "src" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")

        self.assertIn('query: search || ""', page)
        self.assertIn("Confirm clear", page)
        self.assertIn("Payload must be valid JSON", page)
        clear_handler = page[page.index("const handleClearHistory"):page.index("const handleCopy")]
        self.assertLess(clear_handler.index("setRequests([])"), clear_handler.index("void refreshWebhooks(false)"))
        self.assertLess(clear_handler.index("setRequests([])"), clear_handler.index('await apiClient.delete("/webhooks/requests?confirm=CONFIRM")'))
        self.assertIn("historyClearedRef.current && nextRequests.length === 0", page)
        self.assertIn("historyClearedRef.current = true", clear_handler)

    def test_pricetrackr_dashboard_excludes_deleted_rows_and_preserves_ten_minute_frequency(self):
        page = (ROOT / "apps" / "pricetrackr" / "frontend" / "src" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
        form = (ROOT / "apps" / "pricetrackr" / "frontend" / "src" / "app" / "dashboard" / "components" / "AddUrlForm.tsx").read_text(encoding="utf-8")

        self.assertIn("AND deleted_at IS NULL", page)
        self.assertNotIn("parseInt(t.check_frequency_hours)", page)
        self.assertIn('value="0.1666666667"', form)

    def test_pricetrackr_worker_rechecks_trackers_that_need_a_selector(self):
        backend = (ROOT / "apps" / "pricetrackr" / "backend" / "main.py").read_text(encoding="utf-8")

        self.assertIn('TrackedUrl.status.in_(("active", "needs_selector"))', backend)
        self.assertIn('t.status not in ("active", "needs_selector")', backend)

    def test_feedback_uses_namespaced_digest_and_full_refresh_after_mutations(self):
        page = (ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")

        self.assertIn('"/feedbacklens/digest?days=7"', page)
        self.assertIn("await refreshFeedback();", page)

    def test_invoicefollow_exposes_partial_payment_dispute_and_manual_approval_actions(self):
        backend = (ROOT / "apps" / "invoicefollow" / "backend" / "main.py").read_text(encoding="utf-8")
        page = (ROOT / "apps" / "invoicefollow" / "frontend" / "src" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")

        self.assertIn('@invoice_router.post("/{invoice_id}/partial-payment")', backend)
        self.assertIn('@invoice_router.post("/{invoice_id}/dispute")', backend)
        self.assertIn('@invoice_router.post("/{invoice_id}/approve")', backend)
        self.assertIn('"partial-payment"', page)
        self.assertIn('"dispute"', page)
        self.assertIn('"approve"', page)

    def test_unified_digest_route_is_not_claimed_by_feedbacklens(self):
        feedback_backend = (ROOT / "apps" / "feedbacklens" / "backend" / "main.py").read_text(encoding="utf-8")

        self.assertIn('@digest_router.get("/feedbacklens/digest")', feedback_backend)
        self.assertNotIn('@digest_router.get("/digest")', feedback_backend)


class InvoiceFollowActionRegressionTests(unittest.TestCase):
    def _session(self):
        session = SimpleNamespace()
        session.added = []
        session.add = session.added.append
        session.flush = AsyncMock()
        return session

    def _invoice(self):
        return invoicefollow.Invoice(
            id=7,
            user_id=42,
            client_name="Acme",
            client_email="billing@example.test",
            amount=100,
            currency="USD",
            due_date=date(2026, 7, 1),
        )

    def test_partial_payment_persists_payment_and_requires_approval(self):
        invoice = self._invoice()
        session = self._session()
        with patch.object(invoicefollow, "_get_invoice_or_404", AsyncMock(return_value=invoice)):
            response = asyncio.run(invoicefollow.record_partial_payment(
                7,
                invoicefollow.PartialPaymentRequest(amount=25, currency="USD"),
                user=SimpleNamespace(id=42),
                session=session,
            ))

        self.assertEqual(response["status"], "partial")
        self.assertEqual(invoice.amount_paid, 25)
        self.assertTrue(invoice.approval_required)
        self.assertTrue(invoice.cron_paused)
        self.assertTrue(any(isinstance(item, invoicefollow.InvoicePaymentEvent) for item in session.added))

    def test_dispute_then_manual_approval_resumes_the_sequence(self):
        invoice = self._invoice()
        session = self._session()
        getter = AsyncMock(return_value=invoice)
        with patch.object(invoicefollow, "_get_invoice_or_404", getter):
            disputed = asyncio.run(invoicefollow.dispute_invoice(7, user=SimpleNamespace(id=42), session=session))
            approved = asyncio.run(invoicefollow.approve_invoice_action(7, user=SimpleNamespace(id=42), session=session))

        self.assertEqual(disputed["status"], "disputed")
        self.assertEqual(approved["status"], "approved")
        self.assertFalse(invoice.disputed)
        self.assertFalse(invoice.approval_required)
        self.assertFalse(invoice.cron_paused)
        self.assertEqual(invoice.approval_status, "approved")


if __name__ == "__main__":
    unittest.main()
