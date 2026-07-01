from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DevForgeSiteUXContractTest(unittest.TestCase):
    def test_beta_products_keep_clean_price_labels(self):
        products = (ROOT / "packages" / "core" / "lib" / "products.ts").read_text()

        self.assertNotIn("$9.99 beta", products)

    def test_webhook_monitor_uses_consistent_product_name(self):
        products = (ROOT / "packages" / "core" / "lib" / "products.ts").read_text()
        webhook_block = re.search(
            r'slug: "webhookmonitor".*?slug: "feedbacklens"',
            products,
            re.DOTALL,
        )

        self.assertIsNotNone(webhook_block)
        self.assertIn('shortName: "Webhook Monitor"', webhook_block.group(0))

    def test_suite_home_does_not_claim_all_products_are_live(self):
        suite_home = (ROOT / "packages" / "ui" / "components" / "SuiteHomePage.tsx").read_text()

        self.assertNotIn("5 products live", suite_home)
        self.assertIn("liveCount", suite_home)
        self.assertIn("live products", suite_home)
        self.assertIn("betaCount", suite_home)
        self.assertIn("beta pilots", suite_home)

    def test_suite_home_has_high_intent_signup_cta(self):
        suite_home = (ROOT / "packages" / "ui" / "components" / "SuiteHomePage.tsx").read_text()

        self.assertIn('ctaText="Start free"', suite_home)
        self.assertIn('ctaHref="/register?plan=free"', suite_home)
        self.assertIn('href="/register?plan=free"', suite_home)

    def test_product_cards_use_audience_tags_instead_of_audience_paragraph(self):
        product_card = (ROOT / "packages" / "ui" / "components" / "ProductCard.tsx").read_text()

        self.assertNotIn("Who is it for", product_card)
        self.assertIn("audienceTags", product_card)

    def test_feature_cards_use_specific_descriptions(self):
        landing = (ROOT / "packages" / "ui" / "components" / "ProductLandingPage.tsx").read_text()

        self.assertNotIn("Available in the ${product.shortName} workflow", landing)
        self.assertIn("getFeatureDescription", landing)

    def test_nonessential_sections_are_collapsible(self):
        landing = (ROOT / "packages" / "ui" / "components" / "ProductLandingPage.tsx").read_text()

        self.assertIn("<details", landing)
        self.assertIn("Other tools in the same stack", landing)

    def test_shared_site_has_motion_hooks(self):
        styles = (ROOT / "packages" / "ui" / "styles" / "globals.css").read_text()
        demos = (ROOT / "packages" / "ui" / "components" / "ProductDemos.tsx").read_text()
        demo_shell = (ROOT / "packages" / "ui" / "components" / "ProductDemoShell.tsx").read_text()

        self.assertIn("demo-pulse", styles)
        self.assertIn("demo-scanline", styles)
        self.assertIn("demo-pulse", demos)
        self.assertIn("demo-scanline", demo_shell)


if __name__ == "__main__":
    unittest.main()
