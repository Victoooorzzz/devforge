import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "backend_core"))

from data_limits import is_fuzzy_row_count_allowed
from sensitive_data import mask_sensitive_mapping, mask_sensitive_text


class SensitiveDataTests(unittest.TestCase):
    def test_masks_sensitive_headers_without_touching_safe_headers(self):
        masked = mask_sensitive_mapping({
            "authorization": "Bearer secret-token",
            "Stripe-Signature": "t=123,v1=abcdef",
            "content-type": "application/json",
        })

        self.assertEqual(masked["authorization"], "[redacted]")
        self.assertEqual(masked["Stripe-Signature"], "[redacted]")
        self.assertEqual(masked["content-type"], "application/json")

    def test_masks_common_secret_fields_in_body_preview(self):
        body = '{"event":"payment","token":"abc123","nested":{"secret":"hidden"}}'

        masked = mask_sensitive_text(body)

        self.assertIn('"token":"[redacted]"', masked)
        self.assertIn('"secret":"[redacted]"', masked)
        self.assertIn('"event":"payment"', masked)


class DataLimitTests(unittest.TestCase):
    def test_fuzzy_row_limit_allows_boundary_and_blocks_large_inputs(self):
        self.assertTrue(is_fuzzy_row_count_allowed(5000))
        self.assertFalse(is_fuzzy_row_count_allowed(5001))


if __name__ == "__main__":
    unittest.main()
