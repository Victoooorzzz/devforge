import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PAGE = ROOT / "apps" / "webhookmonitor" / "frontend" / "src" / "app" / "dashboard" / "page.tsx"
FEATURE_DOC = ROOT / "docs" / "features" / "webhookmonitor-event-export.md"


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

    def test_feature_contract_doc_exists_for_frontend_implementation(self):
        self.assertTrue(FEATURE_DOC.exists())
        source = FEATURE_DOC.read_text(encoding="utf-8")

        self.assertIn("GET /webhooks/requests/{request_id}/export?format=curl", source)
        self.assertIn("GET /webhooks/requests/{request_id}/export?format=postman", source)
        self.assertIn("Postman Collection v2.1", source)


if __name__ == "__main__":
    unittest.main()
