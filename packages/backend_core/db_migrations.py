from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)


MIGRATION_STATEMENTS = [
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS whitespace_fixed INTEGER DEFAULT 0",
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS error_message VARCHAR",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_promise_date DATE",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS cron_paused BOOLEAN DEFAULT FALSE",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS promise_token VARCHAR",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS min_price DOUBLE PRECISION",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS in_stock BOOLEAN",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS next_check_at TIMESTAMP",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS check_frequency_hours INTEGER DEFAULT 24",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS alert_threshold DOUBLE PRECISION",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS user_id INTEGER",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS last_retry_status INTEGER",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS auto_retry_enabled BOOLEAN DEFAULT FALSE",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS expected_interval_minutes INTEGER DEFAULT 0",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS alert_email VARCHAR DEFAULT ''",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS auto_retry_enabled BOOLEAN DEFAULT FALSE",
    "ALTER TABLE feedback_entries ADD COLUMN IF NOT EXISTS is_urgent BOOLEAN DEFAULT FALSE",
    "ALTER TABLE feedback_entries ADD COLUMN IF NOT EXISTS draft_reply VARCHAR",
    "ALTER TABLE feedback_entries ADD COLUMN IF NOT EXISTS analysis_engine VARCHAR",
    "ALTER TABLE feedback_settings ADD COLUMN IF NOT EXISTS alert_email VARCHAR DEFAULT ''",
    "ALTER TABLE feedback_settings ADD COLUMN IF NOT EXISTS weekly_summary_enabled BOOLEAN DEFAULT TRUE",
    (
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "uq_user_product_access_user_app_idx "
        "ON user_product_access (user_id, app_name)"
    ),
]


async def run_lightweight_migrations(conn: AsyncConnection) -> None:
    for statement in MIGRATION_STATEMENTS:
        await conn.execute(text(statement))
    logger.info("Applied %s lightweight DB migrations", len(MIGRATION_STATEMENTS))
