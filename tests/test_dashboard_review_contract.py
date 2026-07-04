from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


class DashboardReviewContractTest(unittest.TestCase):
    def test_capacity_quotas_render_plan_capacity_as_full_available_limit(self):
        panel = read("packages/ui/components/DashboardPlanPanel.tsx")
        usage = read("packages/ui/components/UsageQuotaCard.tsx")

        self.assertIn('mode?: "usage" | "capacity"', panel)
        self.assertIn('mode: "capacity"', panel)
        self.assertIn("displayUsed", usage)

    def test_filecleaner_dashboard_has_schema_placeholder_and_pipeline_presets(self):
        page = read("apps/filecleaner/frontend/src/app/dashboard/page.tsx")

        self.assertIn("pipelinePresets", page)
        self.assertIn("Sales ops", page)
        self.assertIn("Marketing leads", page)
        self.assertIn("Support tickets", page)
        self.assertIn("required:email, type:number:amount, unique:invoice_id", page)
        self.assertNotIn('{ label: "Max upload size", used: 10, limit: 10', page)
        self.assertNotIn('{ label: "Retention", used: 1, limit: 1', page)

    def test_webhook_dashboard_has_test_event_empty_state_and_clear_retry_controls(self):
        page = read("apps/webhookmonitor/frontend/src/app/dashboard/page.tsx")

        self.assertIn("handleSendTestWebhook", page)
        self.assertIn("Send test webhook", page)
        self.assertIn("Auto retry", page)
        self.assertIn("Copy as cURL", page)
        self.assertIn("Failed forwards are delivery attempts", page)
        self.assertNotRegex(page, r"dd/mm/aaaa", re.IGNORECASE)

    def test_invoicefollow_dashboard_hides_zero_kpis_and_positions_cash_recovery(self):
        page = read("apps/invoicefollow/frontend/src/app/dashboard/page.tsx")

        self.assertIn("hasInvoiceData", page)
        self.assertIn("Cash recovery, not invoice creation", page)
        self.assertIn("Stop dreading your inbox on Mondays", page)
        self.assertIn('placeholder="Invoice #INV-2041 from Clara Studio"', page)
        self.assertIn('placeholder="billing@clarastudio.com"', page)
        self.assertIn('connected ? "text-emerald-500" : "text-zinc-400"', page)
        self.assertNotIn('value: `${metrics?.avg_payment_time_days ?? 0}d`', page)

    def test_pricetrackr_dashboard_avoids_amazon_and_guides_scrapeable_urls(self):
        dashboard = read("apps/pricetrackr/frontend/src/app/dashboard/components/DashboardClient.tsx")
        add_form = read("apps/pricetrackr/frontend/src/app/dashboard/components/AddUrlForm.tsx")
        combined = f"{dashboard}\n{add_form}"

        self.assertNotRegex(combined, r"amazon", re.IGNORECASE)
        self.assertIn("Shopify-friendly URLs", combined)
        self.assertIn("Best Buy", combined)
        self.assertIn("Newegg", combined)
        self.assertIn("Price drop detected", dashboard)
        self.assertIn("Webhook alert preview", dashboard)
        self.assertIn("Add your first product", dashboard)

    def test_feedbacklens_dashboard_has_sample_feedback_sources_cards_and_roi(self):
        page = read("apps/feedbacklens/frontend/src/app/dashboard/page.tsx")

        self.assertIn("loadSampleFeedback", page)
        self.assertIn("Load sample feedback", page)
        self.assertIn("sourceCards", page)
        self.assertIn("Product team saved 8 hours/week", page)
        self.assertIn("Join beta - 50% off first 3 months", page)
        self.assertIn("processed by the system", page)
        self.assertNotIn('limit: 10, caption: "Dedupe stays visible', page)


if __name__ == "__main__":
    unittest.main()
