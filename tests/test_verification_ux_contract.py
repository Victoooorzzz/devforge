from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = ["filecleaner", "invoicefollow", "webhookmonitor", "feedbacklens", "pricetrackr"]

class VerificationUxContractTest(unittest.TestCase):
    def test_login_and_register_do_not_force_unverified_users_to_verify_page(self):
        for product in PRODUCTS:
            for page in ["login", "register"]:
                path = ROOT / "apps" / product / "frontend" / "src" / "app" / page / "page.tsx"
                text = path.read_text()
                self.assertNotIn('router.push("/verify")', text, f"{product} {page} should not block dashboard behind verify")
                self.assertIn('router.push("/dashboard")', text, f"{product} {page} should route successful auth to dashboard")

    def test_pricetrackr_login_uses_shared_auth_flow_only(self):
        text = (ROOT / "apps" / "pricetrackr" / "frontend" / "src" / "app" / "login" / "page.tsx").read_text()

        self.assertIn("auth.login", text)
        self.assertNotIn('fetch("/api/auth"', text)

    def test_verify_pages_use_consistent_white_devforge_branding(self):
        for product in PRODUCTS:
            path = ROOT / "apps" / product / "frontend" / "src" / "app" / "verify" / "page.tsx"
            text = path.read_text()
            self.assertIn('devforge-logo-white.svg', text, product)
            self.assertIn('DevForge', text, product)
            self.assertNotIn("product.name.split", text, product)
            self.assertNotRegex(text, r"text-(emerald|orange|indigo|blue|fuchsia)-500")

    def test_verify_email_uses_theme_tokens_not_hardcoded_indigo_or_green(self):
        text = (ROOT / "packages" / "ui" / "components" / "VerifyEmail.tsx").read_text()
        for token in ["bg-indigo", "text-indigo", "ring-indigo", "shadow-indigo", "text-green"]:
            self.assertNotIn(token, text)
        self.assertIn("var(--color-accent)", text)
        self.assertIn("var(--color-text-secondary)", text)

    def test_feedbacklens_loads_same_inter_font_as_other_products(self):
        text = (ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "app" / "layout.tsx").read_text()
        self.assertIn('import { Inter } from "next/font/google"', text)
        self.assertIn('const inter = Inter({ subsets: ["latin"] })', text)
        self.assertIn('className={`${inter.className} antialiased`}', text)

if __name__ == "__main__":
    unittest.main()
