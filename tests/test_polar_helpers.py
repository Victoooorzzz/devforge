import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "backend_core"))
sys.path.insert(0, str(ROOT / "scripts"))

from polar_utils import (
    build_polar_checkout_payload,
    get_polar_event_user_id,
    resolve_polar_api_url,
    should_activate_for_polar_event,
    should_deactivate_for_polar_event,
)
from create_polar_products import build_product_payload


class PolarCheckoutPayloadTests(unittest.TestCase):
    def test_resolves_polar_api_url_for_sandbox(self):
        self.assertEqual(
            resolve_polar_api_url(server="sandbox", api_url=""),
            "https://sandbox-api.polar.sh/v1",
        )

    def test_explicit_polar_api_url_overrides_server(self):
        self.assertEqual(
            resolve_polar_api_url(server="sandbox", api_url="https://polar.example.test/v1/"),
            "https://polar.example.test/v1",
        )

    def test_checkout_payload_links_polar_customer_to_local_user(self):
        payload = build_polar_checkout_payload(
            user_id=42,
            user_email="victor@example.com",
            product_id="product_123",
            frontend_url="https://filecleaner.devforgeapp.pro",
        )

        self.assertEqual(payload["products"], ["product_123"])
        self.assertEqual(payload["customer_email"], "victor@example.com")
        self.assertEqual(payload["external_customer_id"], "42")
        self.assertEqual(payload["metadata"]["user_id"], "42")
        self.assertEqual(payload["customer_metadata"]["user_id"], "42")
        self.assertIn("checkout_id={CHECKOUT_ID}", payload["success_url"])
        self.assertEqual(payload["return_url"], "https://filecleaner.devforgeapp.pro/dashboard/settings")


class PolarWebhookTests(unittest.TestCase):
    def test_extracts_user_id_from_customer_external_id(self):
        event = {
            "type": "subscription.active",
            "data": {
                "customer": {"external_id": "42"},
                "metadata": {"user_id": "ignored"},
            },
        }

        self.assertEqual(get_polar_event_user_id(event), "42")

    def test_extracts_user_id_from_metadata_fallback(self):
        event = {
            "type": "order.paid",
            "data": {
                "metadata": {"user_id": "99"},
            },
        }

        self.assertEqual(get_polar_event_user_id(event), "99")

    def test_classifies_activation_and_deactivation_events(self):
        self.assertTrue(should_activate_for_polar_event("order.paid"))
        self.assertTrue(should_activate_for_polar_event("subscription.active"))
        self.assertFalse(should_activate_for_polar_event("subscription.revoked"))
        self.assertTrue(should_deactivate_for_polar_event("subscription.revoked"))
        self.assertTrue(should_deactivate_for_polar_event("subscription.canceled"))


class PolarCatalogPayloadTests(unittest.TestCase):
    def test_build_product_payload_creates_monthly_usd_subscription(self):
        payload = build_product_payload(
            app_slug="filecleaner",
            name="File Cleaner",
            description="Clean files fast.",
            price_cents=999,
        )

        self.assertEqual(payload["name"], "File Cleaner")
        self.assertEqual(payload["description"], "Clean files fast.")
        self.assertEqual(payload["recurring_interval"], "month")
        self.assertEqual(payload["visibility"], "public")
        self.assertEqual(payload["metadata"]["devforge_app"], "filecleaner")
        self.assertEqual(payload["prices"], [
            {
                "amount_type": "fixed",
                "price_currency": "usd",
                "price_amount": 999,
            }
        ])


if __name__ == "__main__":
    unittest.main()
