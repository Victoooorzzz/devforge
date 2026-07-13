import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "backend_core"))

from product_insights import (
    build_tracker_health,
    summarize_feedback,
    summarize_files,
    summarize_invoices,
    summarize_trackers,
    summarize_webhooks,
)


class ProductInsightsTests(unittest.TestCase):
    def test_summarizes_filecleaner_quality_metrics(self):
        summary = summarize_files([
            {
                "status": "complete",
                "rows_original": 100,
                "rows_clean": 80,
                "duplicates_removed": 10,
                "empty_removed": 5,
                "whitespace_fixed": 8,
                "report_json": '{"schema_validation":{"invalid_rows":2},"anomaly_detection":{"total_flags":1}}',
            },
            {"status": "error", "rows_original": 0, "rows_clean": 0},
        ])

        self.assertEqual(summary["total_files"], 2)
        self.assertEqual(summary["completed_files"], 1)
        self.assertEqual(summary["error_files"], 1)
        self.assertEqual(summary["rows_saved"], 20)
        self.assertEqual(summary["quality_actions"], 23)
        self.assertEqual(summary["needs_review_files"], 2)

    def test_summarizes_invoice_cash_risk(self):
        today = date(2026, 6, 17)
        summary = summarize_invoices([
            {"status": "pending", "amount": 120.0, "due_date": date(2026, 6, 1)},
            {"status": "pending", "amount": 80.0, "due_date": date(2026, 6, 30), "cron_paused": True},
            {"status": "paid", "amount": 50.0, "due_date": date(2026, 5, 1)},
        ], today=today)

        self.assertEqual(summary["total_invoices"], 3)
        self.assertEqual(summary["pending_amount"], 200.0)
        self.assertEqual(summary["overdue_amount"], 120.0)
        self.assertEqual(summary["promised_amount"], 80.0)
        self.assertEqual(summary["cash_at_risk"], 120.0)

    def test_summarizes_tracker_opportunities(self):
        summary = summarize_trackers([
            {"status": "active", "current_price": 90.0, "previous_price": 100.0, "min_price": 80.0, "in_stock": True},
            {"status": "active", "current_price": 140.0, "previous_price": 120.0, "min_price": 100.0, "in_stock": False},
        ])

        self.assertEqual(summary["total_trackers"], 2)
        self.assertEqual(summary["price_drop_count"], 1)
        self.assertEqual(summary["out_of_stock_count"], 1)
        self.assertEqual(summary["potential_savings"], 50.0)

    def test_builds_tracker_health_from_existing_tracker_state(self):
        now = datetime(2026, 6, 17, 12, 0, 0)
        health = build_tracker_health([
            {"id": 1, "label": "Fresh", "last_checked": now - timedelta(hours=2), "check_frequency_hours": 6, "current_price": 99, "in_stock": True},
            {"id": 2, "label": "Stale", "last_checked": now - timedelta(days=3), "check_frequency_hours": 24, "current_price": 40, "in_stock": True},
            {"id": 3, "label": "Missing", "last_checked": now - timedelta(hours=1), "check_frequency_hours": 24, "current_price": None, "in_stock": True},
            {"id": 4, "label": "No Stock", "last_checked": now - timedelta(hours=1), "check_frequency_hours": 24, "current_price": 20, "in_stock": False},
        ], now=now)

        self.assertEqual([item["health"] for item in health], ["price_missing", "out_of_stock", "stale", "healthy"])
        self.assertEqual(health[0]["severity"], "critical")
        self.assertEqual(health[1]["severity"], "warning")

    def test_summarizes_webhook_reliability(self):
        now = datetime(2026, 6, 17, 12, 0, 0)
        summary = summarize_webhooks([
            {"received_at": now - timedelta(hours=1), "retry_count": 0, "last_retry_status": 200},
            {"received_at": now - timedelta(days=2), "retry_count": 2, "last_retry_status": 500},
            {"received_at": now - timedelta(minutes=5), "retry_count": 1, "last_retry_status": None, "auto_retry_enabled": True},
        ], now=now)

        self.assertEqual(summary["total_requests"], 3)
        self.assertEqual(summary["recent_24h"], 2)
        self.assertEqual(summary["retry_pressure"], 3)
        self.assertEqual(summary["failed_forwards"], 1)
        self.assertEqual(summary["auto_retry_enabled"], 1)

    def test_summarizes_feedback_sentiment_and_themes(self):
        summary = summarize_feedback([
            {"sentiment": "positive", "is_urgent": False, "themes": ["billing", "ux"]},
            {"sentiment": "negative", "is_urgent": True, "themes": ["billing"]},
            {"sentiment": "neutral", "is_urgent": False, "themes_json": '["docs"]'},
        ])

        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["urgent_count"], 1)
        self.assertEqual(summary["sentiment_stats"]["positive"], 1)
        self.assertEqual(summary["sentiment_stats"]["negative"], 1)
        self.assertEqual(summary["top_themes"], ["billing", "ux", "docs"])


if __name__ == "__main__":
    unittest.main()
