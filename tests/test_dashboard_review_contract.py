from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


class DashboardReviewContractTest(unittest.TestCase):
    def test_capacity_quotas_render_as_plan_limits_not_consumed_usage(self):
        panel = read("packages/ui/components/DashboardPlanPanel.tsx")
        usage = read("packages/ui/components/UsageQuotaCard.tsx")

        self.assertIn('mode?: "usage" | "capacity"', panel)
        self.assertIn('mode: "capacity"', panel)
        self.assertIn("isCapacity", usage)
        self.assertIn("Included", usage)
        self.assertIn("minimumUsagePercentage", usage)
        self.assertNotIn("Available based on your current paid plan and backend limits.", panel)
        self.assertNotIn('displayUsed = mode === "capacity" ? limit : used', usage)

    def test_backend_cors_exposes_download_filename_header(self):
        factory = read("packages/backend_core/main_factory.py")

        self.assertIn("expose_headers", factory)
        self.assertIn("Content-Disposition", factory)

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
        next_config = read("apps/webhookmonitor/frontend/next.config.js")

        self.assertIn("handleSendTestWebhook", page)
        self.assertIn("Send test webhook", page)
        self.assertIn("Auto retry", page)
        self.assertIn("Copy as cURL", page)
        self.assertIn("Failed forwards are delivery attempts", page)
        self.assertIn("endpointLimitLabel", page)
        self.assertNotIn("{endpoints.length}/1 Free", page)
        self.assertNotRegex(page, r"dd/mm/aaaa", re.IGNORECASE)
        self.assertIn('source: "/in/:slug"', next_config)
        self.assertIn('destination: `${backendUrl}/in/:slug`', next_config)

    def test_invoicefollow_dashboard_hides_zero_kpis_and_positions_cash_recovery(self):
        page = read("apps/invoicefollow/frontend/src/app/dashboard/page.tsx")

        self.assertIn("hasInvoiceData", page)
        self.assertIn("Cash recovery, not invoice creation", page)
        self.assertIn("Stop dreading your inbox on Mondays", page)
        self.assertIn('placeholder="Invoice #INV-2041 from Clara Studio"', page)
        self.assertIn('placeholder="billing@clarastudio.com"', page)
        self.assertIn('connected ? "text-emerald-500" : "text-zinc-400"', page)
        self.assertIn('invoice.status === "paid" ? "paid"', page)
        self.assertIn("formatAvgPaymentTime", page)
        self.assertIn('apiClient.get<DigestSummary>("/invoicefollow/digest")', page)
        self.assertNotIn('apiClient.get<DigestSummary>("/digest")', page)
        self.assertNotIn('value: `${metrics?.avg_payment_time_days ?? 0}d`', page)

    def test_pricetrackr_dashboard_avoids_amazon_and_guides_scrapeable_urls(self):
        dashboard = read("apps/pricetrackr/frontend/src/app/dashboard/components/DashboardClient.tsx")
        add_form = read("apps/pricetrackr/frontend/src/app/dashboard/components/AddUrlForm.tsx")
        detect_proxy = ROOT / "apps" / "pricetrackr" / "frontend" / "src" / "app" / "api" / "trackers" / "detect" / "route.ts"
        create_proxy = ROOT / "apps" / "pricetrackr" / "frontend" / "src" / "app" / "api" / "trackers" / "route.ts"
        combined = f"{dashboard}\n{add_form}"

        self.assertNotRegex(combined, r"amazon", re.IGNORECASE)
        self.assertIn("Shopify-friendly URLs", combined)
        self.assertIn("Best Buy", combined)
        self.assertIn("Newegg", combined)
        self.assertIn("Price drop detected", dashboard)
        self.assertIn("Webhook alert preview", dashboard)
        self.assertIn("Add your first product", dashboard)
        self.assertTrue(detect_proxy.exists())
        self.assertTrue(create_proxy.exists())
        self.assertIn("Price analysis service is unavailable", detect_proxy.read_text())
        self.assertIn("Price tracker service is unavailable", create_proxy.read_text())
        self.assertIn('fetch("/api/trackers/detect"', add_form)
        self.assertIn('fetch("/api/trackers"', add_form)
        self.assertIn("URL is required.", add_form)
        self.assertIn("setUrlError", add_form)
        self.assertIn("setUrl(normalizedUrl)", add_form)
        self.assertNotIn('apiClient.post<DetectedMetadata>("/trackers/detect"', add_form)
        self.assertNotIn('apiClient.post<TrackedUrl>("/trackers"', add_form)

    def test_pricetrackr_ui_matches_threshold_export_and_soft_delete_contracts(self):
        dashboard = read("apps/pricetrackr/frontend/src/app/dashboard/components/DashboardClient.tsx")
        url_list = read("apps/pricetrackr/frontend/src/app/dashboard/components/UrlList.tsx")
        export_button = read("apps/pricetrackr/frontend/src/app/dashboard/components/ExportButton.tsx")
        urls_route = read("apps/pricetrackr/frontend/src/app/api/urls/route.ts")

        self.assertIn("onThresholdChange", url_list)
        self.assertNotIn("onToggleAlertPanel(t.id); // Triggers state update", url_list)
        self.assertIn("handleAlertThresholdChange", dashboard)
        self.assertIn('/trackers/export-file?format=', export_button)
        self.assertIn("downloadFile", export_button)
        self.assertIn("deleted_at IS NULL", urls_route)
        self.assertIn('<option value={1 / 6}>10m Interval</option>', url_list)
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
