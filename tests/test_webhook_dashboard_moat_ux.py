import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PAGE = ROOT / "apps" / "webhookmonitor" / "frontend" / "src" / "app" / "dashboard" / "page.tsx"
SETTINGS_PAGE = ROOT / "apps" / "webhookmonitor" / "frontend" / "src" / "app" / "dashboard" / "settings" / "page.tsx"
SETTINGS_UX = ROOT / "packages" / "ui" / "components" / "SettingsUX.tsx"
FEATURE_DOC = ROOT / "docs" / "features" / "webhookmonitor-event-export.md"
SPEC_DOCS = [
    ROOT / "docs" / "features" / "webhookmonitor-replay-search-api.md",
    ROOT / "docs" / "features" / "webhookmonitor-signatures-forwarding.md",
    ROOT / "docs" / "features" / "webhookmonitor-plan-limits-retention.md",
    ROOT / "docs" / "features" / "webhookmonitor-cli.md",
]


class WebhookDashboardMoatUxTests(unittest.TestCase):
    def test_dashboard_exposes_diff_and_schema_validation_controls(self):
        source = DASHBOARD_PAGE.read_text(encoding="utf-8")

        self.assertIn("/diff?base_request_id=", source)
        self.assertIn("/validate-schema", source)
        self.assertIn("Compare with previous", source)
        self.assertIn("Validate Schema", source)

    def test_dashboard_exposes_event_curl_and_postman_exports(self):
        source = DASHBOARD_PAGE.read_text(encoding="utf-8")

        self.assertIn("/export?format=curl", source)
        self.assertIn("/export?format=postman", source)
        self.assertIn("Export cURL", source)
        self.assertIn("Export Postman", source)

    def test_dashboard_exposes_replay_search_and_signature_status_controls(self):
        source = DASHBOARD_PAGE.read_text(encoding="utf-8")

        self.assertIn("/webhooks/search", source)
        self.assertIn("/events/${selected.id}/replay", source)
        self.assertIn("Search JSON path", source)
        self.assertIn("Method filter", source)
        self.assertIn("Date from", source)
        self.assertIn("Provider filter", source)
        self.assertIn("Replay target URL", source)
        self.assertIn("Replay exact", source)
        self.assertIn("Replay modified", source)
        self.assertIn("Replay alternate", source)
        self.assertIn("Signature", source)

    def test_settings_expose_signature_retry_fallback_and_alert_destinations(self):
        source = SETTINGS_PAGE.read_text(encoding="utf-8")

        self.assertIn("Signature Provider", source)
        self.assertIn("Signature Secret", source)
        self.assertIn("Retry Attempts", source)
        self.assertIn("Backoff Seconds", source)
        self.assertIn("Forward Timeout", source)
        self.assertIn("Fallback URL", source)
        self.assertIn("Slack Webhook URL", source)
        self.assertIn("Discord Webhook URL", source)

    def test_clear_history_sends_the_backend_confirmation_contract(self):
        dashboard = DASHBOARD_PAGE.read_text(encoding="utf-8")
        settings = SETTINGS_PAGE.read_text(encoding="utf-8")

        self.assertIn('/webhooks/requests?confirm=CONFIRM', dashboard)
        self.assertIn('/webhooks/requests?confirm=CONFIRM', settings)

    def test_dashboard_distinguishes_empty_history_from_empty_search_results(self):
        source = DASHBOARD_PAGE.read_text(encoding="utf-8")

        self.assertIn("hasActiveSearch", source)
        self.assertIn("No deliveries match your search filters", source)
        self.assertIn('if (logsResult.status === "fulfilled")', source)
        self.assertIn('!historyClearedRef.current && !hasServerSearch', source)
        self.assertIn("Clear search", source)
        self.assertNotIn('data.total === 1 ? "" : "ies"', source)

    def test_api_validation_details_are_normalized_before_rendering(self):
        source = SETTINGS_UX.read_text(encoding="utf-8")

        self.assertIn("Array.isArray(detail)", source)
        self.assertIn("JSON.stringify(detail)", source)

    def test_feature_contract_doc_exists_for_frontend_implementation(self):
        self.assertTrue(FEATURE_DOC.exists())
        source = FEATURE_DOC.read_text(encoding="utf-8")

        self.assertIn("GET /webhooks/requests/{request_id}/export?format=curl", source)
        self.assertIn("GET /webhooks/requests/{request_id}/export?format=postman", source)
        self.assertIn("Postman Collection v2.1", source)

    def test_new_feature_contract_docs_exist_for_frontend_implementation(self):
        for doc in SPEC_DOCS:
            self.assertTrue(doc.exists(), f"Missing feature contract doc: {doc}")
            source = doc.read_text(encoding="utf-8")
            self.assertIn("Frontend contract", source)
            self.assertIn("Backend contract", source)


if __name__ == "__main__":
    unittest.main()
