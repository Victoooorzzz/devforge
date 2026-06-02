import unittest
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "backend_core"))

sys.modules.setdefault(
    "httpx",
    types.SimpleNamespace(AsyncClient=object, HTTPStatusError=Exception),
)
bs4_stub = types.ModuleType("bs4")
bs4_stub.BeautifulSoup = object
sys.modules.setdefault("bs4", bs4_stub)

from polar_utils import get_polar_event_product_id
from scraper import _extract_price_from_text
from product_catalog import (
    APP_SLUGS,
    app_slug_from_url,
    normalize_app_slug,
    resolve_app_from_product_id,
    resolve_product_id_for_app,
)
from security_utils import is_public_http_url
from price_alerts import build_price_alerts


class ProductCatalogTests(unittest.TestCase):
    def test_normalizes_known_product_names(self):
        self.assertEqual(normalize_app_slug("File Cleaner"), "filecleaner")
        self.assertEqual(normalize_app_slug("Invoice Follow-up"), "invoicefollow")
        self.assertEqual(normalize_app_slug("webhookmonitor"), "webhookmonitor")
        self.assertIn("feedbacklens", APP_SLUGS)

    def test_resolves_product_ids_from_settings_without_trusting_client(self):
        class Settings:
            polar_product_id_filecleaner = "prod_file"
            polar_product_id_invoicefollow = ""
            next_public_polar_product_id_invoicefollow = "prod_invoice"
            polar_product_id_pricetrackr = "prod_price"
            polar_product_id_webhookmonitor = "prod_webhook"
            polar_product_id_feedbacklens = "prod_feedback"

        self.assertEqual(resolve_product_id_for_app(Settings, "File Cleaner"), "prod_file")
        self.assertEqual(resolve_product_id_for_app(Settings, "invoicefollow"), "prod_invoice")
        self.assertEqual(resolve_app_from_product_id(Settings, "prod_webhook"), "webhookmonitor")
        self.assertIsNone(resolve_app_from_product_id(Settings, "prod_unknown"))

    def test_infers_app_from_product_domain(self):
        self.assertEqual(app_slug_from_url("https://filecleaner.devforgeapp.pro/dashboard"), "filecleaner")
        self.assertEqual(app_slug_from_url("https://invoicefollow.devforgeapp.pro"), "invoicefollow")
        self.assertIsNone(app_slug_from_url("https://devforgeapp.pro"))


class PolarEventProductTests(unittest.TestCase):
    def test_extracts_product_id_from_common_event_shapes(self):
        self.assertEqual(
            get_polar_event_product_id({"data": {"product_id": "prod_1"}}),
            "prod_1",
        )
        self.assertEqual(
            get_polar_event_product_id({"data": {"product": {"id": "prod_2"}}}),
            "prod_2",
        )
        self.assertEqual(
            get_polar_event_product_id({"data": {"products": [{"id": "prod_3"}]}}),
            "prod_3",
        )


class PublicUrlTests(unittest.TestCase):
    def test_allows_only_public_http_urls(self):
        self.assertTrue(is_public_http_url("https://example.com/webhook"))
        self.assertFalse(is_public_http_url("file:///etc/passwd"))
        self.assertFalse(is_public_http_url("http://localhost:8000/hook"))
        self.assertFalse(is_public_http_url("http://127.0.0.1/hook"))
        self.assertFalse(is_public_http_url("http://169.254.169.254/latest/meta-data"))
        self.assertFalse(is_public_http_url("https://10.0.0.1/internal"))


class PriceAlertTests(unittest.TestCase):
    def test_back_in_stock_uses_previous_stock_before_state_update(self):
        alerts = build_price_alerts(
            label="Camera",
            url="https://example.com/camera",
            previous_price=100,
            new_price=95,
            previous_stock=False,
            new_stock=True,
            min_price=90,
            alert_threshold=None,
        )

        self.assertIn("price_drop", alerts)
        self.assertIn("back_in_stock", alerts)

    def test_threshold_alert_is_emitted_when_price_crosses_target(self):
        alerts = build_price_alerts(
            label="Camera",
            url="https://example.com/camera",
            previous_price=120,
            new_price=99,
            previous_stock=True,
            new_stock=True,
            min_price=99,
            alert_threshold=100,
        )

        self.assertIn("target_price", alerts)


class ScraperPriceExtractionTests(unittest.TestCase):
    def test_extracts_common_currency_formats(self):
        self.assertEqual(_extract_price_from_text("\u00a351.77"), 51.77)
        self.assertEqual(_extract_price_from_text("$1,299.99"), 1299.99)
        self.assertEqual(_extract_price_from_text("EUR 1.299,99"), 1299.99)

    def test_price_scraper_does_not_advertise_brotli_without_decoder(self):
        source = (ROOT / "packages" / "backend_core" / "scraper.py").read_text()
        self.assertIn('"Accept-Encoding": "gzip, deflate"', source)
        self.assertNotIn('"Accept-Encoding": "gzip, deflate, br"', source)


class MigrationStatementTests(unittest.TestCase):
    def test_feedback_entries_gets_urgent_column(self):
        statements = (ROOT / "packages" / "backend_core" / "db_migrations.py").read_text()
        self.assertIn("feedback_entries ADD COLUMN IF NOT EXISTS is_urgent", statements)


if __name__ == "__main__":
    unittest.main()
