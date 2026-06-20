import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

from apps.feedbacklens.backend.main import FeedbackPrefsUpdate, FeedbackSettings


class FeedbackSettingsContractTests(unittest.TestCase):
    def test_feedback_threshold_defaults_to_frontend_scale(self):
        settings = FeedbackSettings(user_id=42)

        self.assertEqual(settings.negative_threshold, 0.5)

    def test_feedback_threshold_accepts_decimal_values(self):
        payload = FeedbackPrefsUpdate(negative_threshold=0.4)

        self.assertEqual(payload.negative_threshold, 0.4)

    def test_feedback_threshold_rejects_values_outside_scale(self):
        with self.assertRaises(ValueError):
            FeedbackPrefsUpdate(negative_threshold=4)


if __name__ == "__main__":
    unittest.main()
