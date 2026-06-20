import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


SETTINGS_PAGES = [
    ROOT / "apps" / "filecleaner" / "frontend" / "src" / "app" / "dashboard" / "settings" / "page.tsx",
    ROOT / "apps" / "invoicefollow" / "frontend" / "src" / "app" / "dashboard" / "settings" / "page.tsx",
    ROOT / "apps" / "pricetrackr" / "frontend" / "src" / "app" / "dashboard" / "settings" / "page.tsx",
    ROOT / "apps" / "webhookmonitor" / "frontend" / "src" / "app" / "dashboard" / "settings" / "page.tsx",
    ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "app" / "dashboard" / "settings" / "page.tsx",
]


class FrontendSettingsUxTests(unittest.TestCase):
    def test_settings_pages_use_inline_feedback_instead_of_native_dialogs(self):
        for page in SETTINGS_PAGES:
            with self.subTest(page=page):
                source = page.read_text(encoding="utf-8")

                self.assertNotIn("alert(", source)
                self.assertNotIn("window.confirm", source)
                self.assertIn("ActionToast", source)

    def test_settings_pages_do_not_render_mojibake_status_icons(self):
        broken_markers = ["ð", "â"]

        for page in SETTINGS_PAGES:
            with self.subTest(page=page):
                source = page.read_text(encoding="utf-8")

                for marker in broken_markers:
                    self.assertNotIn(marker, source)

    def test_webhookmonitor_settings_preserve_advanced_preferences(self):
        source = (
            ROOT
            / "apps"
            / "webhookmonitor"
            / "frontend"
            / "src"
            / "app"
            / "dashboard"
            / "settings"
            / "page.tsx"
        ).read_text(encoding="utf-8")

        self.assertIn("expected_interval_minutes", source)
        self.assertIn("alert_email", source)
        self.assertIn("auto_retry_enabled", source)
        self.assertIn("Auto Retry Forwarding", source)
        self.assertIn("Silence Alert Interval", source)

    def test_feedbacklens_settings_normalize_legacy_thresholds(self):
        source = (
            ROOT
            / "apps"
            / "feedbacklens"
            / "frontend"
            / "src"
            / "app"
            / "dashboard"
            / "settings"
            / "page.tsx"
        ).read_text(encoding="utf-8")

        self.assertIn("normalizeNegativeThreshold", source)
        self.assertIn("negative_threshold: normalizeNegativeThreshold", source)


if __name__ == "__main__":
    unittest.main()
