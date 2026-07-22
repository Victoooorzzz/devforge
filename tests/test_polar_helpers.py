import unittest
from pathlib import Path
import sys
from types import SimpleNamespace

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
from create_devforge_polar_products import (
    APPS as TIERED_APPS,
    active_fixed_price_cents,
    build_product_price_update_payload,
    resolve_api_url as resolve_catalog_api_url,
)
from product_catalog import resolve_app_from_product_id, resolve_plan_from_product_id, resolve_product_id_for_app


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

        self.assertEqual(payload["product_id"], "product_123")
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


class ProductCatalogTests(unittest.TestCase):
    def test_resolves_pro_product_id_from_explicit_pro_then_legacy_base_name(self):
        settings = SimpleNamespace(
            polar_product_id_filecleaner_pro="prod_filecleaner_pro",
            next_public_polar_product_id_filecleaner_pro="",
            polar_product_id_filecleaner="prod_filecleaner_legacy",
            next_public_polar_product_id_filecleaner="",
        )

        self.assertEqual(resolve_product_id_for_app(settings, "filecleaner", "pro"), "prod_filecleaner_pro")

        settings.polar_product_id_filecleaner_pro = ""
        self.assertEqual(resolve_product_id_for_app(settings, "filecleaner", "pro"), "prod_filecleaner_legacy")

    def test_resolves_team_product_id_and_plan_from_product_id(self):
        settings = SimpleNamespace(
            polar_product_id_filecleaner="prod_filecleaner_pro",
            next_public_polar_product_id_filecleaner="",
            polar_product_id_filecleaner_team="prod_filecleaner_team",
            next_public_polar_product_id_filecleaner_team="",
        )

        self.assertEqual(resolve_product_id_for_app(settings, "filecleaner", "team"), "prod_filecleaner_team")
        self.assertEqual(resolve_app_from_product_id(settings, "prod_filecleaner_team"), "filecleaner")
        self.assertEqual(resolve_plan_from_product_id(settings, "prod_filecleaner_team"), "team")
        self.assertEqual(resolve_plan_from_product_id(settings, "prod_filecleaner_pro"), "pro")


class PolarCatalogPayloadTests(unittest.TestCase):
    def test_tiered_catalog_matches_frontend_prices(self):
        prices = {
            app.slug: (app.pro_price_cents, app.team_price_cents)
            for app in TIERED_APPS
        }

        self.assertEqual(prices["feedbacklens"], (1900, 7900))
        for app_slug in ("filecleaner", "invoicefollow", "pricetrackr", "webhookmonitor"):
            self.assertEqual(prices[app_slug], (999, 4900))

    def test_tiered_catalog_uses_sandbox_api_when_requested(self):
        self.assertEqual(
            resolve_catalog_api_url(server="sandbox"),
            "https://sandbox-api.polar.sh/v1",
        )

    def test_tiered_catalog_detects_and_replaces_wrong_fixed_price(self):
        product = {
            "prices": [
                {
                    "amount_type": "fixed",
                    "price_amount": 999,
                    "price_currency": "usd",
                    "is_archived": False,
                }
            ]
        }

        self.assertEqual(active_fixed_price_cents(product), 999)
        self.assertEqual(
            build_product_price_update_payload(1900),
            {
                "prices": [
                    {
                        "amount_type": "fixed",
                        "price_currency": "usd",
                        "price_amount": 1900,
                    }
                ]
            },
        )

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
