import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PAGE = ROOT / "apps" / "webhookmonitor" / "frontend" / "src" / "app" / "dashboard" / "page.tsx"


class WebhookDashboardMoatUxTests(unittest.TestCase):
    def test_dashboard_exposes_diff_and_schema_validation_controls(self):
        source = DASHBOARD_PAGE.read_text(encoding="utf-8")

        self.assertIn("/diff?base_request_id=", source)
        self.assertIn("/validate-schema", source)
        self.assertIn("Compare with previous", source)
        self.assertIn("Validate Schema", source)


if __name__ == "__main__":
    unittest.main()
