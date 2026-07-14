import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class FrontendFeatureTruthfulnessContractTests(unittest.TestCase):
    def test_feedbacklens_hides_external_connectors_and_github_actions(self):
        dashboard = read("apps/feedbacklens/frontend/src/app/dashboard/page.tsx")
        self.assertIn("const SHOW_EXTERNAL_SOURCE_CONNECTORS = false;", dashboard)
        self.assertIn("const SHOW_GITHUB_ISSUE_ACTION = false;", dashboard)

    def test_invoicefollow_hides_external_connections_in_dashboard_and_settings(self):
        dashboard = read("apps/invoicefollow/frontend/src/app/dashboard/page.tsx")
        settings = read("apps/invoicefollow/frontend/src/app/dashboard/settings/page.tsx")
        self.assertIn("const SHOW_EXTERNAL_CONNECTIONS = false;", dashboard)
        self.assertIn("const SHOW_EXTERNAL_CONNECTIONS = false;", settings)

    def test_public_product_copy_does_not_sell_unavailable_feedback_integrations(self):
        products = read("packages/core/lib/products.ts")
        feedback = products[products.index('slug: "feedbacklens"'):products.index('slug: "pricetrackr"')]
        for unavailable_claim in ("GitHub Issue action", "GitHub Issues", "All channels", "Source connectors", "Manual + email sources", "more channels"):
            self.assertNotIn(unavailable_claim, feedback)

        product_config = read("apps/feedbacklens/frontend/src/config/product.ts")
        self.assertNotIn("GitHub, Canny, X, and Reddit sources", product_config)

        product_landing = read("packages/ui/components/ProductLandingPage.tsx")
        self.assertNotIn('"GitHub Issue action"', product_landing)

    def test_public_product_copy_does_not_sell_unavailable_invoice_connections(self):
        products = read("packages/core/lib/products.ts")
        invoice = products[products.index('slug: "invoicefollow"'):]
        for unavailable_claim in ("Gmail sync", "Stripe and PayPal", "Limited PayPal", "Payment connections", "Stripe/PayPal state"):
            self.assertNotIn(unavailable_claim, invoice)

        product_config = read("apps/invoicefollow/frontend/src/config/product.ts")
        self.assertNotIn("Stripe read-only payment matching", product_config)
        self.assertNotIn("Team users and PayPal matching", product_config)
        self.assertNotIn("detect payments", product_config)

        landing_page = read("apps/invoicefollow/frontend/src/app/page.tsx")
        self.assertNotIn("reconcile payments", landing_page)

        product_landing = read("packages/ui/components/ProductLandingPage.tsx")
        self.assertNotIn('"Stripe/PayPal state"', product_landing)
        self.assertNotIn('"Gmail sync"', product_landing)

    def test_plan_panel_does_not_unlock_unavailable_integrations(self):
        plan_panel = read("packages/ui/components/DashboardPlanPanel.tsx")
        self.assertNotIn('feedbacklens: ["GitHub issue creation"', plan_panel)
        self.assertNotIn('invoicefollow: ["Gmail sync", "Stripe/PayPal reconciliation"', plan_panel)


if __name__ == "__main__":
    unittest.main()
