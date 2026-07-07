import unittest
from datetime import datetime, timedelta
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
# Insert paths so we can import packages and the pricetrackr app modules
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "apps" / "pricetrackr" / "backend"))

from apps.pricetrackr.backend.main import (
    extract_price,
    trigger_alerts,
    TrackedUrl,
    generate_slug,
    _detect_scrape_block,
)
from backend_core.plan_limits import (
    PRICETRACKR_LIMITS,
    reject_price_frequency_if_needed,
    reject_tracker_count_if_needed,
)

class PriceTrackrUnitTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        pass

    def test_price_extraction_scenarios(self):
        # Standard USD formatting
        self.assertEqual(extract_price("$1,299.99"), 1299.99)
        self.assertEqual(extract_price("Price: $450.00 USD"), 450.00)

        # European formatting (comma for decimal, dot/space for thousands)
        self.assertEqual(extract_price("99,99 €"), 99.99)
        self.assertEqual(extract_price("1.250,50 EUR"), 1250.50)

        # Simple integer
        self.assertEqual(extract_price("S/. 45"), 45.0)

        # Text prefix and suffix
        self.assertEqual(extract_price("Buy now for only $12.50 today!"), 12.50)

        # Invalid and bounds checking
        self.assertIsNone(extract_price("no price here"))
        self.assertIsNone(extract_price("$0.00")) # Below 0.01 minimum
        self.assertIsNone(extract_price("$1,000,000.00")) # Exceeds 999,999 bounds

    def test_slug_generation(self):
        self.assertTrue(generate_slug("iPhone 15 Pro").startswith("iphone-15-pro-"))
        self.assertTrue(generate_slug("Súper Laptop 2024!!!").startswith("s-per-laptop-2024-"))
        self.assertEqual(len(generate_slug("Simple Label").split("-")[-1]), 6) # hex suffix length

    def test_price_extraction_handles_space_thousands(self):
        self.assertEqual(extract_price("1 234,56 EUR"), 1234.56)

    def test_scrape_block_detection_and_lightweight_fetch_contract(self):
        backend = (ROOT / "apps" / "pricetrackr" / "backend" / "main.py").read_text(encoding="utf-8")
        requirements = (ROOT / "apps" / "pricetrackr" / "backend" / "requirements.txt").read_text(encoding="utf-8")
        public_page = (ROOT / "apps" / "pricetrackr" / "frontend" / "src" / "app" / "p" / "[slug]" / "page.tsx").read_text(encoding="utf-8")

        self.assertEqual(_detect_scrape_block(403, ""), "blocked")
        self.assertEqual(_detect_scrape_block(200, "<title>Cloudflare CAPTCHA</title>"), "blocked")
        self.assertIn("curl_cffi", requirements)
        self.assertIn("CurlAsyncSession", backend)
        self.assertNotIn("playwright", backend.lower())
        self.assertNotIn("selenium", backend.lower())
        self.assertIn("history.svg?slug=", public_page)

    def test_plan_limits_enforcement(self):
        free_limits = PRICETRACKR_LIMITS["free"]
        pro_limits = PRICETRACKR_LIMITS["pro"]

        # Frequency limit checking (Free limit is 24h, Pro is 1h)
        reject_price_frequency_if_needed("pro", pro_limits, 1) # should pass
        reject_price_frequency_if_needed("free", free_limits, 24) # should pass

        with self.assertRaises(Exception):
            reject_price_frequency_if_needed("free", free_limits, 12)
        with self.assertRaises(Exception):
            reject_price_frequency_if_needed("free", free_limits, 1)

        # Tracker count limit checking (Free limit is 5, Pro is 100)
        reject_tracker_count_if_needed("pro", pro_limits, 99) # should pass
        reject_tracker_count_if_needed("free", free_limits, 4) # should pass

        with self.assertRaises(Exception):
            reject_tracker_count_if_needed("free", free_limits, 5)
        with self.assertRaises(Exception):
            reject_tracker_count_if_needed("free", free_limits, 6)

    @patch("apps.pricetrackr.backend.main.send_email")
    async def test_alert_rate_limiting_by_type_and_direction(self, mock_send_email):
        # Create a mock database session
        session = AsyncMock()

        # Track sent alerts simulated database
        sent_alerts = []

        async def mock_execute(query, params=None):
            q_str = str(query)
            if "SELECT" in q_str and "pt_alert_logs" in q_str:
                tracker_id = params["tracker_id"]
                change_type = params["change_type"]
                direction = params["direction"]
                limit_time = params["limit_time"]
                matching = [
                    a for a in sent_alerts
                    if a["tracker_id"] == tracker_id and a["change_type"] == change_type and a["direction"] == direction and a["sent_at"] >= limit_time
                ]
                res_mock = MagicMock()
                if matching:
                    res_mock.fetchone.return_value = (matching[-1]["sent_at"],)
                else:
                    res_mock.fetchone.return_value = None
                return res_mock
            elif "INSERT INTO pt_alert_logs" in q_str:
                sent_alerts.append({
                    "tracker_id": params["tracker_id"],
                    "change_type": params["change_type"],
                    "direction": params["direction"],
                    "sent_at": params["sent_at"]
                })
                return MagicMock()
            else:
                # Mock TrackerSettings lookup
                mock_settings_result = MagicMock()
                mock_settings = MagicMock()
                mock_settings.alert_email = "test@example.com"
                mock_settings_result.scalar_one_or_none.return_value = mock_settings
                return mock_settings_result

        session.execute = AsyncMock(side_effect=mock_execute)

        tracker = TrackedUrl(
            id=123,
            user_id=1,
            url="https://example.com/test",
            label="Test Laptop",
            current_price=100.0,
            alert_threshold=90.0,
            status="active"
        )

        # Trigger price drop alert
        await trigger_alerts(
            t=tracker,
            previous_price=120.0,
            new_price=80.0,
            previous_stock=True,
            new_stock=True,
            last_text="Normal",
            new_text="Normal",
            session=session
        )

        # Should send 2 alerts initially (one for price drop "bajó", one for "target" price reached)
        self.assertEqual(mock_send_email.call_count, 2)

        # Trigger again immediately (within rate limit window of 6 hours for price)
        await trigger_alerts(
            t=tracker,
            previous_price=80.0,
            new_price=75.0,
            previous_stock=True,
            new_stock=True,
            last_text="Normal",
            new_text="Normal",
            session=session
        )

        # Call count should remain 2 due to DB rate limiting
        self.assertEqual(mock_send_email.call_count, 2)


if __name__ == "__main__":
    unittest.main()
