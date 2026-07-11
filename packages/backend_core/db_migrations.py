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
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS promise_used_at TIMESTAMP",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS promise_expires_at TIMESTAMP",
    (
        "UPDATE invoices SET promise_expires_at = COALESCE(created_at, NOW()) + INTERVAL '30 days' "
        "WHERE promise_token IS NOT NULL AND promise_expires_at IS NULL"
    ),
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS currency VARCHAR DEFAULT 'USD'",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS issued_date DATE",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS invoice_number VARCHAR DEFAULT ''",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'import'",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS source_message_id VARCHAR DEFAULT ''",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS thread_id VARCHAR DEFAULT ''",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS schedule_paused_until DATE",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS manual_review_reason VARCHAR DEFAULT ''",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS notes VARCHAR DEFAULT ''",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
    "ALTER TABLE invoice_settings ADD COLUMN IF NOT EXISTS templates_json TEXT DEFAULT ''",
    "ALTER TABLE invoice_settings ADD COLUMN IF NOT EXISTS company_name VARCHAR DEFAULT ''",
    "ALTER TABLE invoice_settings ADD COLUMN IF NOT EXISTS send_hour INTEGER DEFAULT 9",
    "ALTER TABLE invoice_settings ADD COLUMN IF NOT EXISTS skip_weekends BOOLEAN DEFAULT TRUE",
    "ALTER TABLE invoice_settings ADD COLUMN IF NOT EXISTS timezone VARCHAR DEFAULT 'America/Lima'",
    "ALTER TABLE invoice_settings ADD COLUMN IF NOT EXISTS sender_name VARCHAR DEFAULT ''",
    "ALTER TABLE invoice_settings ADD COLUMN IF NOT EXISTS weekly_digest_enabled BOOLEAN DEFAULT TRUE",
    "ALTER TABLE invoice_settings ADD COLUMN IF NOT EXISTS immediate_alerts_enabled BOOLEAN DEFAULT TRUE",
    "ALTER TABLE invoice_settings ADD COLUMN IF NOT EXISTS no_send_after_hour INTEGER DEFAULT 18",
    (
        "CREATE TABLE IF NOT EXISTS invoice_integration_settings ("
        "user_id INTEGER PRIMARY KEY, "
        "gmail_connected BOOLEAN DEFAULT FALSE, gmail_email VARCHAR DEFAULT '', gmail_state VARCHAR DEFAULT '', "
        "gmail_access_token TEXT DEFAULT '', gmail_refresh_token TEXT DEFAULT '', gmail_token_expires_at TIMESTAMP, "
        "outlook_connected BOOLEAN DEFAULT FALSE, outlook_email VARCHAR DEFAULT '', outlook_state VARCHAR DEFAULT '', "
        "outlook_access_token TEXT DEFAULT '', outlook_refresh_token TEXT DEFAULT '', outlook_token_expires_at TIMESTAMP, "
        "stripe_connected BOOLEAN DEFAULT FALSE, stripe_account_label VARCHAR DEFAULT '', stripe_api_key TEXT DEFAULT '', "
        "paypal_connected BOOLEAN DEFAULT FALSE, paypal_account_label VARCHAR DEFAULT '', paypal_client_id TEXT DEFAULT '', paypal_client_secret TEXT DEFAULT '', "
        "forward_address_token VARCHAR DEFAULT '', created_at TIMESTAMP, updated_at TIMESTAMP)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS invoice_detected_drafts ("
        "id SERIAL PRIMARY KEY, user_id INTEGER, source VARCHAR DEFAULT 'email', source_message_id VARCHAR DEFAULT '', "
        "raw_subject VARCHAR DEFAULT '', raw_body VARCHAR DEFAULT '', sender_email VARCHAR DEFAULT '', sender_name VARCHAR DEFAULT '', "
        "client_name VARCHAR DEFAULT '', client_email VARCHAR DEFAULT '', amount DOUBLE PRECISION DEFAULT 0, currency VARCHAR DEFAULT 'USD', "
        "due_date DATE, issued_date DATE, invoice_number VARCHAR DEFAULT '', confidence DOUBLE PRECISION DEFAULT 0, "
        "status VARCHAR DEFAULT 'needs_review', parsed_json TEXT DEFAULT '{}', created_at TIMESTAMP)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS invoice_reminder_logs ("
        "id SERIAL PRIMARY KEY, invoice_id INTEGER, user_id INTEGER, stage_day INTEGER, template_key VARCHAR DEFAULT '', "
        "status VARCHAR DEFAULT 'queued', provider VARCHAR DEFAULT 'gmail', subject VARCHAR DEFAULT '', body_preview VARCHAR DEFAULT '', "
        "response_intent VARCHAR DEFAULT '', response_excerpt VARCHAR DEFAULT '', sent_at TIMESTAMP)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS invoice_reply_events ("
        "id SERIAL PRIMARY KEY, invoice_id INTEGER, user_id INTEGER, provider VARCHAR DEFAULT 'gmail', provider_message_id VARCHAR DEFAULT '', text VARCHAR DEFAULT '', "
        "intent_label VARCHAR DEFAULT 'DESCONOCIDO', action_taken VARCHAR DEFAULT '', received_at TIMESTAMP)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS invoice_payment_events ("
        "id SERIAL PRIMARY KEY, user_id INTEGER, invoice_id INTEGER, provider VARCHAR DEFAULT 'stripe', provider_event_id VARCHAR DEFAULT '', "
        "amount DOUBLE PRECISION DEFAULT 0, currency VARCHAR DEFAULT 'USD', status VARCHAR DEFAULT 'succeeded', raw_json TEXT DEFAULT '{}', detected_at TIMESTAMP)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS invoice_public_rate_limits ("
        "id SERIAL PRIMARY KEY, bucket VARCHAR NOT NULL, client_key VARCHAR NOT NULL, "
        "window_started_at TIMESTAMP NOT NULL, request_count INTEGER DEFAULT 1, expires_at TIMESTAMP NOT NULL, "
        "CONSTRAINT uq_invoice_public_rate_limit_window UNIQUE (bucket, client_key, window_started_at))"
    ),
    "CREATE INDEX IF NOT EXISTS idx_invoice_public_rate_limits_expires_at ON invoice_public_rate_limits (expires_at)",
    (
        "DO $$ DECLARE target RECORD; BEGIN FOR target IN SELECT * FROM (VALUES "
        "('invoice_public_rate_limits','window_started_at'), "
        "('invoice_public_rate_limits','expires_at'), "
        "('invoices','promise_used_at'), ('invoices','promise_expires_at'), "
        "('invoices','paid_at'), ('invoices','created_at'), ('invoices','updated_at'), "
        "('invoice_integration_settings','gmail_token_expires_at'), "
        "('invoice_integration_settings','created_at'), ('invoice_integration_settings','updated_at'), "
        "('invoice_detected_drafts','created_at'), ('invoice_reminder_logs','sent_at'), "
        "('invoice_reply_events','received_at'), ('invoice_payment_events','detected_at'), "
        "('invoice_audit_logs','created_at')"
        ") AS utc_columns(table_name, column_name) LOOP "
        "IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() "
        "AND information_schema.columns.table_name = target.table_name "
        "AND information_schema.columns.column_name = target.column_name "
        "AND data_type = 'timestamp without time zone') THEN "
        "EXECUTE format('ALTER TABLE %I ALTER COLUMN %I TYPE TIMESTAMPTZ USING %I AT TIME ZONE ''UTC''', "
        "target.table_name, target.column_name, target.column_name); END IF; END LOOP; END $$;"
    ),
    (
        "CREATE TABLE IF NOT EXISTS invoice_audit_logs ("
        "id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, actor_user_id INTEGER, actor_type VARCHAR DEFAULT 'user', "
        "entity_type VARCHAR DEFAULT 'invoice', entity_id INTEGER, action VARCHAR NOT NULL, source VARCHAR DEFAULT 'api', "
        "source_event_id VARCHAR NOT NULL, details_json TEXT DEFAULT '{}', created_at TIMESTAMP, "
        "CONSTRAINT uq_invoice_audit_source_action UNIQUE (user_id, source, source_event_id, action))"
    ),
    "CREATE INDEX IF NOT EXISTS idx_invoice_audit_logs_user_created ON invoice_audit_logs (user_id, created_at)",
    "ALTER TABLE invoice_integration_settings ADD COLUMN IF NOT EXISTS gmail_access_token TEXT DEFAULT ''",
    "ALTER TABLE invoice_integration_settings ADD COLUMN IF NOT EXISTS gmail_refresh_token TEXT DEFAULT ''",
    "ALTER TABLE invoice_integration_settings ADD COLUMN IF NOT EXISTS gmail_token_expires_at TIMESTAMP",
    "ALTER TABLE invoice_integration_settings ADD COLUMN IF NOT EXISTS outlook_access_token TEXT DEFAULT ''",
    "ALTER TABLE invoice_integration_settings ADD COLUMN IF NOT EXISTS outlook_refresh_token TEXT DEFAULT ''",
    "ALTER TABLE invoice_integration_settings ADD COLUMN IF NOT EXISTS outlook_token_expires_at TIMESTAMP",
    "ALTER TABLE invoice_integration_settings ADD COLUMN IF NOT EXISTS stripe_api_key TEXT DEFAULT ''",
    "ALTER TABLE invoice_integration_settings ADD COLUMN IF NOT EXISTS paypal_client_id TEXT DEFAULT ''",
    "ALTER TABLE invoice_integration_settings ADD COLUMN IF NOT EXISTS paypal_client_secret TEXT DEFAULT ''",
    "ALTER TABLE invoice_reply_events ADD COLUMN IF NOT EXISTS provider_message_id VARCHAR DEFAULT ''",
    (
        "UPDATE invoice_integration_settings SET forward_address_token = "
        "md5(random()::text || clock_timestamp()::text || user_id::text) "
        "WHERE COALESCE(forward_address_token, '') = ''"
    ),
    (
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_invoice_integration_forward_address_token "
        "ON invoice_integration_settings (forward_address_token) WHERE forward_address_token <> ''"
    ),
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
    (
        "DO $$ DECLARE index_name text; BEGIN "
        "FOR index_name IN "
        "SELECT indexname FROM pg_indexes "
        "WHERE schemaname = current_schema() "
        "AND tablename = 'webhook_endpoints' "
        "AND indexdef ILIKE 'CREATE UNIQUE INDEX%' "
        "AND indexdef LIKE '%(user_id)%' "
        "LOOP "
        "EXECUTE format('DROP INDEX IF EXISTS %I', index_name); "
        "END LOOP; END $$;"
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
    (
        "CREATE TABLE IF NOT EXISTS webhook_event_idempotency ("
        "id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, endpoint_id INTEGER NOT NULL, "
        "provider_event_id VARCHAR NOT NULL, request_id INTEGER, created_at TIMESTAMP, "
        "CONSTRAINT uq_webhook_event_idempotency UNIQUE (user_id, endpoint_id, provider_event_id))"
    ),
    "CREATE INDEX IF NOT EXISTS idx_webhook_event_idempotency_user_id ON webhook_event_idempotency (user_id)",
    "CREATE INDEX IF NOT EXISTS idx_webhook_event_idempotency_endpoint_id ON webhook_event_idempotency (endpoint_id)",
    "CREATE INDEX IF NOT EXISTS idx_webhook_event_idempotency_request_id ON webhook_event_idempotency (request_id)",
    (
        "CREATE TABLE IF NOT EXISTS webhook_audit_logs ("
        "id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, action VARCHAR NOT NULL, "
        "entity_type VARCHAR NOT NULL, entity_id INTEGER, details_json VARCHAR DEFAULT '{}', "
        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    ),
    "CREATE INDEX IF NOT EXISTS idx_webhook_audit_logs_user_id ON webhook_audit_logs (user_id)",
    "CREATE INDEX IF NOT EXISTS idx_webhook_audit_logs_created_at ON webhook_audit_logs (created_at)",
    (
        "CREATE TABLE IF NOT EXISTS webhook_cron_rate_limits ("
        "id SERIAL PRIMARY KEY, job_name VARCHAR NOT NULL, window_started_at TIMESTAMP NOT NULL, "
        "request_count INTEGER DEFAULT 1, expires_at TIMESTAMP NOT NULL, "
        "CONSTRAINT uq_webhook_cron_rate_window UNIQUE (job_name, window_started_at))"
    ),
    "CREATE INDEX IF NOT EXISTS idx_webhook_cron_rate_limits_expires_at ON webhook_cron_rate_limits (expires_at)",
    (
        "CREATE INDEX IF NOT EXISTS ix_webhook_replay_dedup ON webhook_requests "
        "(user_id, replay_of_request_id, path, body, received_at)"
    ),
    (
        "DO $$ BEGIN IF NOT EXISTS ("
        "SELECT 1 FROM pg_constraint WHERE conname = 'fk_webhook_requests_replay'"
        ") THEN ALTER TABLE webhook_requests ADD CONSTRAINT fk_webhook_requests_replay "
        "FOREIGN KEY (replay_of_request_id) REFERENCES webhook_requests(id) ON DELETE SET NULL; "
        "END IF; END $$;"
    ),
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
    "ALTER TABLE feedback_entries ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'manual'",
    "ALTER TABLE feedback_entries ADD COLUMN IF NOT EXISTS author VARCHAR DEFAULT ''",
    "ALTER TABLE feedback_entries ADD COLUMN IF NOT EXISTS source_url VARCHAR DEFAULT ''",
    "ALTER TABLE feedback_entries ADD COLUMN IF NOT EXISTS source_message_id VARCHAR DEFAULT ''",
    "ALTER TABLE feedback_entries ADD COLUMN IF NOT EXISTS cluster_slug VARCHAR DEFAULT ''",
    "ALTER TABLE feedback_entries ADD COLUMN IF NOT EXISTS priority VARCHAR DEFAULT 'low'",
    "ALTER TABLE feedback_entries ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ",
    "ALTER TABLE feedback_entries ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMPTZ",
    "UPDATE feedback_entries SET updated_at = created_at WHERE updated_at IS NULL",
    "ALTER TABLE feedback_entries ALTER COLUMN updated_at SET NOT NULL",
    (
        "DELETE FROM feedback_entries newer USING feedback_entries older "
        "WHERE newer.id > older.id AND newer.user_id = older.user_id "
        "AND newer.source = older.source AND newer.source_message_id = older.source_message_id "
        "AND newer.source_message_id <> ''"
    ),
    (
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_feedback_entries_user_source_message_id_nonempty "
        "ON feedback_entries (user_id, source, source_message_id) WHERE source_message_id <> ''"
    ),
    "ALTER TABLE feedback_settings ADD COLUMN IF NOT EXISTS alert_email VARCHAR DEFAULT ''",
    "ALTER TABLE feedback_settings ADD COLUMN IF NOT EXISTS weekly_summary_enabled BOOLEAN DEFAULT TRUE",
    "ALTER TABLE feedback_settings ADD COLUMN IF NOT EXISTS timezone VARCHAR DEFAULT 'UTC'",
    "ALTER TABLE feedback_settings ADD COLUMN IF NOT EXISTS last_weekly_digest_at TIMESTAMPTZ",
    "ALTER TABLE feedback_settings ALTER COLUMN negative_threshold TYPE DOUBLE PRECISION USING negative_threshold::double precision",
    "ALTER TABLE feedback_settings ALTER COLUMN negative_threshold SET DEFAULT 0.5",
    "UPDATE feedback_settings SET negative_threshold = 0.5 WHERE negative_threshold > 1",
    (
        "DO $$ BEGIN "
        "IF to_regclass('feedback_entries') IS NOT NULL AND EXISTS ("
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = 'feedback_entries' AND column_name = 'created_at' "
        "AND data_type <> 'timestamp with time zone'"
        ") THEN "
        "ALTER TABLE feedback_entries ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'; "
        "END IF; END $$;"
    ),
    (
        "DO $$ BEGIN "
        "IF to_regclass('feedback_settings') IS NOT NULL AND EXISTS ("
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = 'feedback_settings' AND column_name = 'last_weekly_digest_at' "
        "AND data_type <> 'timestamp with time zone'"
        ") THEN "
        "ALTER TABLE feedback_settings ALTER COLUMN last_weekly_digest_at TYPE TIMESTAMPTZ USING last_weekly_digest_at AT TIME ZONE 'UTC'; "
        "END IF; END $$;"
    ),
    (
        "CREATE TABLE IF NOT EXISTS feedback_sources ("
        "id SERIAL PRIMARY KEY, user_id INTEGER, source_type VARCHAR DEFAULT 'manual', display_name VARCHAR DEFAULT '', "
        "handle VARCHAR DEFAULT '', status VARCHAR DEFAULT 'connected', access_token VARCHAR DEFAULT '', refresh_token VARCHAR DEFAULT '', "
        "webhook_secret VARCHAR DEFAULT '', config_json TEXT DEFAULT '{}', forward_token VARCHAR DEFAULT '', "
        "last_polled_at TIMESTAMPTZ, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)"
    ),
    "ALTER TABLE feedback_sources ADD COLUMN IF NOT EXISTS access_token TEXT DEFAULT ''",
    "ALTER TABLE feedback_sources ADD COLUMN IF NOT EXISTS refresh_token TEXT DEFAULT ''",
    "ALTER TABLE feedback_sources ADD COLUMN IF NOT EXISTS webhook_secret TEXT DEFAULT ''",
    "ALTER TABLE feedback_sources ADD COLUMN IF NOT EXISTS config_json TEXT DEFAULT '{}'",
    "ALTER TABLE feedback_sources ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'connected'",
    "ALTER TABLE feedback_sources ADD COLUMN IF NOT EXISTS last_polled_at TIMESTAMPTZ",
    "ALTER TABLE feedback_sources ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ",
    "ALTER TABLE feedback_sources ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ",
    (
        "DO $$ BEGIN "
        "IF to_regclass('feedback_sources') IS NOT NULL AND EXISTS ("
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = 'feedback_sources' AND column_name = 'last_polled_at' "
        "AND data_type <> 'timestamp with time zone'"
        ") THEN "
        "ALTER TABLE feedback_sources ALTER COLUMN last_polled_at TYPE TIMESTAMPTZ USING last_polled_at AT TIME ZONE 'UTC'; "
        "END IF; "
        "IF to_regclass('feedback_sources') IS NOT NULL AND EXISTS ("
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = 'feedback_sources' AND column_name = 'created_at' "
        "AND data_type <> 'timestamp with time zone'"
        ") THEN "
        "ALTER TABLE feedback_sources ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'; "
        "END IF; "
        "IF to_regclass('feedback_sources') IS NOT NULL AND EXISTS ("
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = 'feedback_sources' AND column_name = 'updated_at' "
        "AND data_type <> 'timestamp with time zone'"
        ") THEN "
        "ALTER TABLE feedback_sources ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'; "
        "END IF; END $$;"
    ),
    (
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "uq_user_product_access_user_app_idx "
        "ON user_product_access (user_id, app_name)"
    ),
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS selector_1 VARCHAR",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS selector_2 VARCHAR",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS selector_3 VARCHAR",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS last_text VARCHAR",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT TRUE",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS slack_webhook_url VARCHAR",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS discord_webhook_url VARCHAR",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS slug VARCHAR",
    "ALTER TABLE price_history ADD COLUMN IF NOT EXISTS text_content VARCHAR",
    "ALTER TABLE price_history ADD COLUMN IF NOT EXISTS metadata_json VARCHAR DEFAULT '{}'",
    (
        "CREATE TABLE IF NOT EXISTS scrape_logs ("
        "id SERIAL PRIMARY KEY, tracker_id INTEGER, timestamp TIMESTAMP, "
        "user_agent VARCHAR, status_code INTEGER, retry BOOLEAN)"
    ),
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS pending_price DOUBLE PRECISION",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS pending_stock BOOLEAN",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS pending_text VARCHAR",
    "ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_tracked_urls_slug_unique ON tracked_urls (slug) WHERE slug IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS idx_tracked_urls_user_status_deleted ON tracked_urls (user_id, status, deleted_at)",
    "CREATE INDEX IF NOT EXISTS idx_price_history_recorded_at ON price_history (recorded_at)",
    (
        "CREATE TABLE IF NOT EXISTS scrape_control ("
        "id INTEGER PRIMARY KEY DEFAULT 1, locked_at TIMESTAMP, "
        "consecutive_high_pressure INTEGER DEFAULT 0)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS pt_export_jobs ("
        "id UUID PRIMARY KEY, user_id INTEGER, status VARCHAR(20) DEFAULT 'pending', "
        "format VARCHAR(10) DEFAULT 'csv', r2_url VARCHAR, error_message VARCHAR, "
        "created_at TIMESTAMP, completed_at TIMESTAMP)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS pt_alert_logs ("
        "id SERIAL PRIMARY KEY, tracker_id INTEGER NOT NULL, "
        "change_type VARCHAR(20) NOT NULL, direction VARCHAR(20) NOT NULL, "
        "sent_at TIMESTAMP NOT NULL DEFAULT NOW())"
    ),
    "CREATE INDEX IF NOT EXISTS idx_invoices_cron_paused ON invoices (cron_paused)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_user_status_due ON invoices (user_id, status, due_date)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_client_identity ON invoices (client_email, client_name)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_invoices_promise_token ON invoices (promise_token) WHERE promise_token IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS idx_invoice_drafts_user_status ON invoice_detected_drafts (user_id, status)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_invoice_payment_provider_event ON invoice_payment_events (provider, provider_event_id) WHERE provider_event_id <> ''",
    (
        "DELETE FROM invoice_reply_events newer USING invoice_reply_events older "
        "WHERE newer.id > older.id AND newer.user_id = older.user_id "
        "AND newer.provider = older.provider AND newer.provider_message_id = older.provider_message_id "
        "AND newer.provider_message_id <> ''"
    ),
    (
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_invoice_reply_events_provider_message "
        "ON invoice_reply_events (user_id, provider, provider_message_id) WHERE provider_message_id <> ''"
    ),
    "CREATE INDEX IF NOT EXISTS idx_invoice_reminder_invoice_stage_status ON invoice_reminder_logs (invoice_id, template_key, status)",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS last_silence_alert_sent_at TIMESTAMP",
    "ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS ip_address VARCHAR",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS ip_whitelist VARCHAR DEFAULT ''",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS ip_blacklist VARCHAR DEFAULT ''",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS json_schema VARCHAR DEFAULT ''",
    "ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS schema_validation_enabled BOOLEAN DEFAULT FALSE",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS schema_valid BOOLEAN",
    "ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS schema_error VARCHAR DEFAULT ''",
]



async def run_lightweight_migrations(conn: AsyncConnection) -> None:
    for statement in MIGRATION_STATEMENTS:
        await conn.execute(text(statement))
    logger.info("Applied %s lightweight DB migrations", len(MIGRATION_STATEMENTS))
