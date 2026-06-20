from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)


MIGRATION_STATEMENTS = [
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS whitespace_fixed INTEGER DEFAULT 0",
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS error_message VARCHAR",
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS raw_object_key VARCHAR",
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS cleaned_object_key VARCHAR",
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS report_object_key VARCHAR",
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS detection_json TEXT DEFAULT '{}'",
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS config_json TEXT DEFAULT '{}'",
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS report_json TEXT DEFAULT '{}'",
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0",
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS notify_email VARCHAR",
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS notify_webhook_url VARCHAR",
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP",
    "UPDATE processed_files SET status = 'completed' WHERE status = 'complete'",
    "UPDATE processed_files SET status = 'failed' WHERE status = 'error'",
    "UPDATE processed_files SET status = 'pending' WHERE status = 'queued'",
    "UPDATE processed_files SET updated_at = created_at WHERE updated_at IS NULL",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_promise_date DATE",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS cron_paused BOOLEAN DEFAULT FALSE",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS promise_token VARCHAR",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS min_price DOUBLE PRECISION",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS in_stock BOOLEAN",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS next_check_at TIMESTAMP",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS check_frequency_hours INTEGER DEFAULT 24",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS alert_threshold DOUBLE PRECISION",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS user_id INTEGER",
    "ALTER TABLE webhook_endpoints ADD COLUMN IF NOT EXISTS name VARCHAR DEFAULT 'Default endpoint'",
    "ALTER TABLE webhook_endpoints ADD COLUMN IF NOT EXISTS allowed_methods_json VARCHAR DEFAULT '[\"POST\",\"PUT\",\"PATCH\",\"DELETE\"]'",
    "ALTER TABLE webhook_endpoints ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
    "ALTER TABLE webhook_endpoints ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()",
    (
        "DO $$ DECLARE constraint_name text; BEGIN "
        "SELECT tc.constraint_name INTO constraint_name "
        "FROM information_schema.table_constraints tc "
        "JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name "
        "WHERE tc.table_name = 'webhook_endpoints' "
        "AND tc.constraint_type = 'UNIQUE' "
        "AND ccu.column_name = 'user_id' LIMIT 1; "
        "IF constraint_name IS NOT NULL THEN "
        "EXECUTE format('ALTER TABLE webhook_endpoints DROP CONSTRAINT %I', constraint_name); "
        "END IF; END $$;"
    ),
    "CREATE EXTENSION IF NOT EXISTS pgcrypto",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS request_uuid VARCHAR",
    "UPDATE webhook_requests SET request_uuid = gen_random_uuid()::text WHERE request_uuid IS NULL",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS query_params_json VARCHAR DEFAULT '{}'",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS ip_address VARCHAR DEFAULT ''",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS forward_error VARCHAR DEFAULT ''",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS signature_valid BOOLEAN",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS signature_error VARCHAR DEFAULT ''",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS signature_provider VARCHAR DEFAULT ''",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS replay_of_request_id INTEGER",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS replay_target_url VARCHAR DEFAULT ''",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS replay_status VARCHAR DEFAULT ''",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS last_retry_status INTEGER",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS auto_retry_enabled BOOLEAN DEFAULT FALSE",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS fallback_url VARCHAR DEFAULT ''",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS expected_interval_minutes INTEGER DEFAULT 0",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS alert_email VARCHAR DEFAULT ''",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS slack_webhook_url VARCHAR DEFAULT ''",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS discord_webhook_url VARCHAR DEFAULT ''",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS auto_retry_enabled BOOLEAN DEFAULT FALSE",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS retry_max_attempts INTEGER DEFAULT 3",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS retry_backoff_seconds_json VARCHAR DEFAULT '[1, 2, 4]'",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS forward_timeout_seconds INTEGER DEFAULT 30",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS signature_provider VARCHAR DEFAULT ''",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS signature_secret VARCHAR DEFAULT ''",
    "ALTER TABLE feedback_entries ADD COLUMN IF NOT EXISTS is_urgent BOOLEAN DEFAULT FALSE",
    "ALTER TABLE feedback_entries ADD COLUMN IF NOT EXISTS draft_reply VARCHAR",
    "ALTER TABLE feedback_entries ADD COLUMN IF NOT EXISTS analysis_engine VARCHAR",
    "ALTER TABLE feedback_settings ADD COLUMN IF NOT EXISTS alert_email VARCHAR DEFAULT ''",
    "ALTER TABLE feedback_settings ADD COLUMN IF NOT EXISTS weekly_summary_enabled BOOLEAN DEFAULT TRUE",
    "ALTER TABLE feedback_settings ALTER COLUMN negative_threshold TYPE DOUBLE PRECISION USING negative_threshold::double precision",
    "ALTER TABLE feedback_settings ALTER COLUMN negative_threshold SET DEFAULT 0.5",
    "UPDATE feedback_settings SET negative_threshold = 0.5 WHERE negative_threshold > 1",
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
