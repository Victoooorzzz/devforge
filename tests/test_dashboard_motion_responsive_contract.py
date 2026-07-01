from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


PRODUCTS = [
    "filecleaner",
    "invoicefollow",
    "webhookmonitor",
    "feedbacklens",
    "pricetrackr",
]


class DashboardMotionResponsiveContractTest(unittest.TestCase):
    def test_shared_dashboard_motion_classes_exist(self):
        styles = (ROOT / "packages" / "ui" / "styles" / "globals.css").read_text()

        for token in [
            ".dashboard-shell",
            ".dashboard-main",
            ".dashboard-motion",
            ".dashboard-card-motion",
            ".dashboard-progress-bar",
            "@keyframes dashboardEnter",
            "@keyframes dashboardProgress",
            "prefers-reduced-motion",
        ]:
            self.assertIn(token, styles)

    def test_all_product_dashboard_layouts_use_responsive_shell_classes(self):
        for product in PRODUCTS:
            layout_path = ROOT / "apps" / product / "frontend" / "src" / "app" / "dashboard" / "layout.tsx"
            layout = layout_path.read_text()

            self.assertIn("dashboard-shell", layout, product)
            self.assertIn("dashboard-sidebar", layout, product)
            self.assertIn("dashboard-main", layout, product)
            self.assertIn("min-w-0", layout, product)

    def test_dashboard_shared_cards_have_motion_and_progress_animation(self):
        files = [
            ROOT / "packages" / "ui" / "components" / "DashboardPlanPanel.tsx",
            ROOT / "packages" / "ui" / "components" / "UsageQuotaCard.tsx",
            ROOT / "packages" / "ui" / "components" / "MetricCard.tsx",
            ROOT / "packages" / "ui" / "components" / "UpgradePrompt.tsx",
            ROOT / "packages" / "ui" / "components" / "IntegrationCard.tsx",
        ]

        combined = "\n".join(path.read_text() for path in files)
        self.assertIn("dashboard-motion", combined)
        self.assertIn("dashboard-card-motion", combined)
        self.assertIn("dashboard-progress-bar", combined)

    def test_dashboard_tables_keep_mobile_overflow_inside_components(self):
        table_files = [
            ROOT / "apps" / "filecleaner" / "frontend" / "src" / "app" / "dashboard" / "page.tsx",
            ROOT / "apps" / "invoicefollow" / "frontend" / "src" / "app" / "dashboard" / "page.tsx",
            ROOT / "apps" / "webhookmonitor" / "frontend" / "src" / "app" / "dashboard" / "page.tsx",
        ]

        for path in table_files:
            text = path.read_text()
            self.assertIn("dashboard-table-scroll", text, str(path))

    def test_pricetrackr_dashboard_has_mobile_motion_hooks(self):
        client = (
            ROOT
            / "apps"
            / "pricetrackr"
            / "frontend"
            / "src"
            / "app"
            / "dashboard"
            / "components"
            / "DashboardClient.tsx"
        ).read_text()

        self.assertIn("dashboard-motion", client)
        self.assertIn("dashboard-card-motion", client)


if __name__ == "__main__":
    unittest.main()
