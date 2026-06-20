import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PAGE = ROOT / "apps" / "webhookmonitor" / "frontend" / "src" / "app" / "dashboard" / "settings" / "page.tsx"


class WebhookForwardRulesUxTests(unittest.TestCase):
    def test_settings_page_exposes_conditional_forwarding_rules(self):
        source = SETTINGS_PAGE.read_text(encoding="utf-8")

        self.assertIn("/webhooks/forward-rules", source)
        self.assertIn("Conditional Forwarding", source)
        self.assertIn("match_path", source)
        self.assertIn("fallback_url", source)
        self.assertIn("Delete Rule", source)


if __name__ == "__main__":
    unittest.main()
