# InvoiceFollow, WebhookMonitor, FeedbackLens Bug Checklist

Source: `C:\Users\victor\.codex\attachments\406103be-ef9f-41c5-b1e7-fe7bec878f43\goal-objective.md`

Status legend:
- `[ ]` Pending
- `[~]` In progress / partially mitigated
- `[x]` Resolved and verified
- `[n/a]` Not applicable to the confirmed product architecture

Final status (2026-07-11): **127 resolved, 1 not applicable, 0 pending, 0 in progress**.

## Confirmed Production Architecture

- Database: Neon Postgres.
- Backend: Render (`backend_core.universal_main`).
- Frontends: Vercel.
- Queues and periodic processing: authenticated cron jobs plus the Postgres-backed `system_outbox`.
- Billing/subscriptions: Polar.
- Invoice payment reconciliation: Stripe.
- User file storage: Cloudflare R2.
- Explicitly excluded: PayPal and Redis.

## InvoiceFollow

### Critical

- [x] IF-01: Remove hardcoded encryption fallback and require `ENCRYPTION_KEY`.
- [x] IF-02: Replace in-memory public rate limiting with distributed/shared limiting or fail-safe abstraction.
- [x] IF-03: Require Stripe webhook signature verification; reject unsigned payloads when secret is missing.
- [x] IF-04: Add per-user email send rate limiting in addition to monthly quota.

### High

- [x] IF-05: Preserve timezone-aware UTC datetimes instead of stripping `tzinfo`.
- [x] IF-06: Make cron reminder/payment jobs safe against concurrent workers and duplicate processing.
- [x] IF-07: Add unique constraint/guarantee for `Invoice.promise_token`.
- [x] IF-08: Add unique compound constraint for `InvoiceReplyEvent(user_id, provider, provider_message_id)`.
- [x] IF-09: Make CSV invoice import limit checks atomic.

### Medium

- [x] IF-10: Build reminder schedule from real reminder logs rather than elapsed days alone.
- [x] IF-11: Harden reply-intent regexes/input limits against ReDoS.
- [x] IF-12: Deduplicate mark-paid endpoint implementation.
- [n/a] IF-13: PayPal sandbox detection is outside the product architecture; DevForge uses Polar and Stripe.
- [x] IF-14: Guarantee uniqueness of `forward_address_token`.
- [x] IF-15: Validate `InvoiceUpdate` amount, status, currency, due date, and email fields.
- [x] IF-16: Make public promise links idempotent, expiring, and auditable.
- [x] IF-17: Support common international amount formats in `_clean_import_amount`.
- [x] IF-18: Return a safe company fallback from `_sender_company`.
- [x] IF-19: Count matched provider payments, not every scanned event, in payment polling metrics.
- [x] IF-20: Require `message_id` for forwarded email invoice detection.
- [x] IF-21: Guard invalid send windows in `is_time_to_send`.
- [x] IF-22: Replace dummy `Invoice` template preview object with an explicit preview object or safe helper.
- [x] IF-23: Invalidate Gmail OAuth state after successful callback.
- [x] IF-24: Paginate Stripe payment events.
- [x] IF-25: Avoid 100+ sequential Gmail message requests when fetching replies.
- [x] IF-26: Add audit trail for automated reply-intent actions.
- [x] IF-27: Track who updated invoice settings.
- [x] IF-28: Stream or page invoice export instead of loading everything into memory.
- [x] IF-29: Default `weekly_digest_enabled` to opt-in false.
- [x] IF-30: Default `immediate_alerts_enabled` to opt-in false.
- [x] IF-31: Align InvoiceFollow timezone-aware Python datetimes with Neon `TIMESTAMPTZ` columns.

## WebhookMonitor

### Critical

- [x] WM-001: Make `IntegrationsCrypto._fernets` concurrency-safe.
- [x] WM-002: Persist/enqueue webhook forwarding before returning success; remove lossy `BackgroundTasks` path.
- [x] WM-003: Add webhook idempotency for provider/event IDs.
- [x] WM-061: Remove WebhookMonitor's public encryption fallback and require `ENCRYPTION_KEY` for integration secrets.

### High

- [x] WM-004: Stop raising generic exceptions for downstream business failures.
- [x] WM-005: Replace broad `except Exception` blocks with specific handling or cancellation-safe re-raise.
- [x] WM-006: Add real pagination for webhook/log listing endpoints.
- [x] WM-007: Add health check endpoint.
- [x] WM-008: Add operational metrics endpoint/counters.

### Medium

- [x] WM-009: Optimize `cleanup_old_logs` N+1 deletes.
- [x] WM-010: Cache JSON Schema validation in hot path.
- [x] WM-011: Bound `process_scheduled_retries` batch size.
- [x] WM-012: Fix `list_logs` Python-side filtering after SQL limit.
- [x] WM-013: Avoid partial commit inconsistencies in `process_webhook_forward`.
- [x] WM-014: Distinguish timeout, DNS failure, and refused connection.
- [x] WM-015: Fix `list_endpoint_events` Python-side filtering after SQL limit.
- [x] WM-016: Prevent retrying successful requests.
- [x] WM-017: Preserve `Content-Type` when forwarding.
- [x] WM-018: Add circuit breaker for failing downstream targets.
- [x] WM-019: Add IP rate limiting to ingestion.
- [x] WM-020: Add delivery-confirmation state usable by clients.
- [x] WM-021: Avoid duplicate request creation when `_persist_and_forward(request_id=None)`.
- [x] WM-022: Harden `_read_body_with_limit` for chunked bodies.
- [x] WM-023: Verify ownership before deleting endpoint-related requests.

### Low

- [x] WM-024: Add compound index for replay deduplication.
- [x] WM-025: Use SQL aggregation for webhook summary.
- [x] WM-026: Stream webhook log export.
- [x] WM-027: Revisit `signature_secret` indexing/documentation.
- [x] WM-028: Move cleanup imports to module scope where appropriate.
- [x] WM-029: Treat 3xx redirects intentionally.
- [x] WM-030: Allow replay query-param overrides.
- [x] WM-031: Preserve richer forward error detail.
- [x] WM-032: Bound or normalize `schema_error`.
- [x] WM-033: Make `_request_export_url` robust to relative paths.
- [x] WM-034: Remove side effect from `get_config`.
- [x] WM-035: Make `WebhookRequest.user_id` nullability explicit.
- [x] WM-036: Capture response body on replay failures.
- [x] WM-037: Avoid adding duplicate `Z` to timezone-aware HAR datetimes.
- [x] WM-038: Clarify multi-timestamp Stripe signature parsing behavior.
- [x] WM-039: Improve OpenAPI export for nested arrays.
- [x] WM-040: Validate `allowed_methods_json` stored config.
- [x] WM-041: Make `_diff_values` handle non-serializable values.
- [x] WM-042: Log IP blacklist rejections.
- [x] WM-043: Surface missing notification settings instead of returning silently.
- [x] WM-044: Include schema validation fields in log exports.
- [x] WM-045: Add auth section to Postman export.
- [x] WM-046: Normalize timezone comparisons.
- [x] WM-047: Alert on invalid retry backoff config instead of silently falling back.
- [x] WM-048: Validate webhook signature secret type.
- [x] WM-049: Log invalid PEM details safely.
- [x] WM-050: Add FK for `replay_of_request_id`.
- [x] WM-051: Support negative indexes in `_extract_match_value`.
- [x] WM-052: Rate limit cron endpoints.
- [x] WM-053: Add batch operations.
- [x] WM-054: Add analytics endpoints.
- [x] WM-055: Support binary payloads.
- [x] WM-056: Add API versioning.
- [x] WM-057: Add soft delete.
- [x] WM-058: Add audit log.
- [x] WM-059: Add scheduled exports.
- [x] WM-060: Support multiple signatures per endpoint.

## FeedbackLens

### Critical

- [x] FL-01: Fix impossible positive sentiment branch.
- [x] FL-02: Remove or negation-check global failure scoring.
- [x] FL-03: Add atomic dedupe constraint for `(user_id, source, source_message_id)`.
- [x] FL-04: Escape user text in urgent alert email HTML.

### High

- [x] FL-05: Prioritize compound cluster terms like dark mode before generic terms.
- [x] FL-06: Preserve non-ASCII text during normalization.
- [x] FL-07: Count login/sign-in as failure only near problem words.
- [x] FL-08: Encrypt OAuth/manual tokens and webhook secrets at rest.
- [x] FL-09: Avoid O(n^2) cluster rebuilds on every request.
- [x] FL-10: Avoid loading 500 dedupe candidates per insert.
- [x] FL-11: Avoid bulk-import candidate loading explosion.
- [x] FL-12: Stream feedback export instead of loading all entries.
- [x] FL-13: Disable or externalize heavyweight ML globals by default.

### Medium

- [x] FL-14: Reduce excessive global failure penalties.
- [x] FL-15: Add real `updated_at`/`analyzed_at`.
- [x] FL-16: Remove dead `mention_count >= 2` logic or implement real count.
- [x] FL-17: Replace domain `HTTPException` in cleaning helper with business exception.
- [x] FL-18: Validate JSON payload/config structures with Pydantic schemas.
- [x] FL-19: Run sync email sending off the event loop.
- [x] FL-20: Reject GitHub webhooks when secret is missing.
- [x] FL-21: Add public webhook rate limiting.
- [x] FL-22: Guard HTTP integrations against SSRF through redirects/final URLs.
- [x] FL-23: Validate CSV upload content type.
- [x] FL-24: Add cursor-based pagination.
- [x] FL-25: Make text truncation safe for languages without spaces.
- [x] FL-26: Optimize dedupe summary.
- [x] FL-27: Make spam terms configurable.
- [x] FL-28: Reduce domain false positives in spam filtering.

### Low

- [x] FL-29: Make priority/topic terms configurable or model-assisted.
- [x] FL-30: Make support draft replies topic-specific.
- [x] FL-31: Validate payload-to-ORM reconstruction.
- [x] FL-32: Validate alert email format.
- [x] FL-33: Add OAuth refresh flow.
- [x] FL-34: Encrypt manually provided tokens.
- [x] FL-35: Replace ad-hoc stopwords/stemming with a robust tokenizer/stemmer.

## Cross-Project Prevention Skill

- [x] SKILL-01: Create a reusable Codex skill/checklist to prevent recurring SaaS bugs: secret fallbacks, unsigned webhooks, in-memory limits, non-atomic dedupe, XSS in email HTML, naive datetimes, unbounded exports, broad exception handling, missing pagination, and missing deploy readiness checks.

## FileCleaner Addendum

- [x] FC-01: PDF cleaning must return one valid cleaned PDF with the original page count, not a ZIP containing one image per page. The output must preserve a PDF filename/content type and remain compatible with Cloudflare R2 storage.

## Resolution Details

The verification commands below are the focused GREEN suites. RED regression tests were added before the corresponding production changes.

### InvoiceFollow Resolved Bugs

| ID | Root cause | What changed | Verification |
| --- | --- | --- | --- |
| IF-01 | Missing `ENCRYPTION_KEY` selected a public fallback key. | Integration crypto now fails closed and requires the environment key. | `python -m unittest tests.test_invoicefollow_production_pipeline -v` |
| IF-03 | Stripe webhook payloads could be parsed without a configured secret/signature. | The public webhook rejects missing configuration and unsigned payloads before processing events. | `python -m unittest tests.test_invoicefollow_production_pipeline -v` |
| IF-04 | Only the monthly email quota was enforced. | Added a per-user recent-send guard before reminder jobs enqueue email. | `python -m unittest tests.test_invoicefollow_production_pipeline -v` |
| IF-05 | UTC timestamps were made naive by stripping `tzinfo`. | `_utc_now()` now preserves timezone-aware UTC values. | `python -m unittest tests.test_invoicefollow_production_pipeline -v` |
| IF-07 | Promise-token uniqueness existed only by probability/application behavior. | Added database-backed uniqueness for non-null promise tokens plus a Neon migration. | `python -m unittest tests.test_invoicefollow_production_pipeline -v`; migration contract test |
| IF-08 | Reply dedupe used a race-prone check before insert. | Added database-backed compound uniqueness for non-empty provider message IDs plus a Neon migration. | `python -m unittest tests.test_invoicefollow_production_pipeline -v`; migration contract test |
| IF-10 | Reminder UI status was inferred from overdue days. | Schedule status is now derived from persisted sent reminder logs. | `python -m unittest tests.test_invoicefollow_production_pipeline -v` |
| IF-15 | Partial updates accepted invalid amount/status/currency values. | Added request-model validation so invalid invoice updates fail before persistence. | `python -m unittest tests.test_invoicefollow_production_pipeline -v` |
| IF-16 | Promise links were reusable forever. | Added 30-day expiry, single-use persistence and `promise_used_at`; existing tokens receive a migration backfill. | `python -m unittest tests.test_invoicefollow_production_pipeline -v`; migration contract test |
| IF-18 | Sender cleanup could remove every character and return blank. | Added a final `Unknown` company fallback. | `python -m unittest tests.test_invoicefollow_production_pipeline -v` |
| IF-19 | Polling metrics counted every scanned payment event. | `processed` now increments only for matched invoice payments. | `python -m unittest tests.test_invoicefollow_production_pipeline -v` |
| IF-20 | Forward ingestion allowed an empty provider message ID. | Forwarded-email requests now require a non-empty `message_id`. | `python -m unittest tests.test_invoicefollow_production_pipeline -v` |
| IF-21 | Invalid send windows silently prevented all reminders. | Runtime scheduling now fails safely when start/end hours are inconsistent. | `python -m unittest tests.test_invoicefollow_production_pipeline -v` |
| IF-23 | Gmail OAuth state remained reusable after callback success. | The state is cleared in the persisted integration settings after token exchange. | `python -m unittest tests.test_invoicefollow_production_pipeline -v` |
| IF-29 | Weekly digests were enabled without explicit consent. | Default changed to opt-in `false`. | `python -m unittest tests.test_invoicefollow_production_pipeline -v` |
| IF-30 | Immediate alerts were enabled without explicit consent. | Default changed to opt-in `false`. | `python -m unittest tests.test_invoicefollow_production_pipeline -v` |
| IF-31 | Live cron passed aware UTC values through SQLAlchemy columns typed as timezone-naive, causing asyncpg `DataError` during overdue status updates. | All persisted InvoiceFollow timestamps now use `DateTime(timezone=True)` and an idempotent Neon migration converts legacy columns to `TIMESTAMPTZ ... AT TIME ZONE 'UTC'`. | Live cron reproduction; model/migration regression; full suite 331 tests OK; Neon column inspection |
| IF-02 | The public limiter lived in one Python process. | Replaced it with an atomic Neon upsert keyed by bucket, hashed client and minute window; accepted hits commit immediately and the table has a cleanup expiry. | `test_public_rate_limit_uses_atomic_neon_counter`; InvoiceFollow 54 tests OK |
| IF-06 | Two Render workers could run the same reminder/payment cron simultaneously. | Added Neon advisory locks around singleton cron jobs; a second worker exits with `skipped_locked`. | `test_cron_jobs_skip_when_neon_advisory_lock_is_already_held`; 54 tests OK |
| IF-09 | Import capacity used count-then-insert without serialization. | Import/create capacity checks now take a per-user Neon transaction advisory lock and fail closed if the count cannot be read. | Atomic import and Neon failure tests; 54 tests OK |
| IF-11 | Reply regex processing accepted unbounded bodies. | Input is capped before normalization and matching, preventing regex work from scaling with attacker-controlled message size. | `test_reply_intent_caps_input_before_normalization_and_regex_matching`; 54 tests OK |
| IF-12 | POST and PUT mark-paid routes duplicated domain logic. | Both methods now call one persisted mark-paid helper. | `test_mark_paid_methods_share_one_domain_helper`; 54 tests OK |
| IF-14 | Forward-address tokens lacked a database guarantee. | Added high-entropy defaults, Neon backfill for blanks and a partial unique index. | Token/model test plus migration contract; 54 tests OK |
| IF-17 | Amount parsing assumed US separators. | Added deterministic handling for European, Peruvian, currency-prefix and accounting formats. | `test_import_amount_accepts_common_international_formats`; 54 tests OK |
| IF-22 | Template preview instantiated a real ORM invoice with no ID. | Replaced it with an explicit non-persistent preview value object. | `test_template_preview_uses_explicit_non_persistent_object`; 54 tests OK |
| IF-24 | Stripe event polling read one page only. | Added bounded pagination using `starting_after` and stops on empty/repeated cursors. | `test_stripe_event_polling_pages_with_starting_after`; 54 tests OK |
| IF-25 | Gmail reply polling fetched message details sequentially. | Added bounded async concurrency for detail requests. | `test_gmail_message_details_use_bounded_concurrency`; 54 tests OK |
| IF-26 | Automated reply actions changed invoice state without durable attribution. | Added idempotent `invoice_audit_logs` entries keyed by provider event/action. | `test_reply_poll_records_automated_action_audit`; migration contract; 54 tests OK |
| IF-27 | Settings changes recorded no actor. | Settings updates now write an authenticated-user audit event. | `test_settings_update_records_authenticated_actor`; 54 tests OK |
| IF-28 | Export loaded every invoice into memory. | Export iterates Neon in bounded pages before streaming the response. | `test_invoice_export_reads_neon_in_bounded_pages`; 54 tests OK |

### WebhookMonitor Resolved Bugs

| ID | Root cause | What changed | Verification |
| --- | --- | --- | --- |
| WM-001 | Fernet cache mutation was unsynchronized. | Cache access is lock-protected and exposes immutable key collections. | `python -m unittest tests.test_webhook_spec_completion tests.test_webhook_monitor_moat -v` |
| WM-002 | Forwarding lived only in an in-process background task after HTTP 200. | Ingestion now persists a `system_outbox` forwarding job before acknowledging receipt. | `python -m unittest tests.test_webhook_spec_completion tests.test_webhook_monitor_moat -v` |
| WM-003 | Repeated provider events could create repeated deliveries. | Added provider-event idempotency persisted in Neon with a compound unique constraint. | Focused WebhookMonitor suite; migration contract test |
| WM-004 | Expected downstream HTTP failures raised generic exceptions. | Forwarding now returns structured failed results for business-level delivery failures. | Focused WebhookMonitor suite |
| WM-006 | List endpoints used fixed limits without client pagination. | Added bounded `limit`/`offset` pagination. | Focused WebhookMonitor suite |
| WM-007 | The product had no dedicated health endpoint. | Added `/webhooks/health`. | Focused WebhookMonitor suite |
| WM-008 | Operators lacked persisted request counters. | Added `/webhooks/metrics` using SQL counts. | Focused WebhookMonitor suite |
| WM-011 | Scheduled retries loaded every due row. | Added a fixed batch bound per cron execution. | Focused WebhookMonitor suite |
| WM-012 | Logs were limited in SQL and then filtered in Python, producing short pages. | Status filtering now occurs in SQL before pagination. | Focused WebhookMonitor suite |
| WM-015 | Endpoint events repeated the same post-limit filtering bug. | Status filtering now occurs in SQL before pagination. | Focused WebhookMonitor suite |
| WM-016 | Successful deliveries could be retried manually. | Retry endpoint rejects already successful requests. | Focused WebhookMonitor suite |
| WM-017 | Forwarding could lose the original media type. | Safe forwarded headers preserve `Content-Type`. | Focused WebhookMonitor suite |
| WM-022 | Body limits could be bypassed by chunked transfer. | The streaming reader enforces the cumulative byte limit. | Focused WebhookMonitor suite |
| WM-023 | Endpoint cleanup deleted related rows before ownership was proven. | Ownership is checked first and unowned IDs return 404. | Focused WebhookMonitor suite |
| WM-009 | Cleanup loaded users and issued one delete per user. | Retention is resolved in bulk and users are grouped by retention period, producing one SQL delete per retention group. | `test_cleanup_old_logs_deletes_once_per_retention_group`; focused suite 35 tests OK |
| WM-010 | JSON Schema validators were rebuilt for every webhook. | Added an LRU cache keyed by schema text for compiled Draft 2020-12 validators. | `test_compiled_json_schema_is_cached_by_schema_text`; focused suite 35 tests OK |
| WM-014 | All network failures collapsed into one generic forwarding error. | Added safe classification for timeout, DNS lookup, refused connection, generic connection and network failures. | Timeout/DNS/refused regression tests; focused suite 35 tests OK |
| WM-019 | Public ingestion had no per-IP multi-worker limit. | Added a Neon-backed sliding one-minute count over persisted requests and returns 429 at the bounded threshold. | `test_ingestion_enforces_database_backed_per_ip_rate_limit`; focused suite 35 tests OK |
| WM-021 | The legacy persistence helper could create another request when no request ID was supplied. | The helper now requires an already persisted request ID; ingestion owns the single durable insert path. | `test_persist_and_forward_requires_an_existing_request`; focused suite 35 tests OK |
| WM-061 | Missing `ENCRYPTION_KEY` silently derived a public fallback key. | Webhook integration crypto now fails closed; a secure key was generated directly in Render after Neon was verified to contain no legacy secrets. | RED missing-key test; GREEN `test_crypto_rejects_missing_encryption_key`; full suite 331 tests OK |
| WM-005 | Broad handlers could swallow task cancellation. | Async notification/network boundaries now re-raise `CancelledError` and log bounded operational failures. | Cancellation-safe source contract; WebhookMonitor suite 58 tests OK |
| WM-013 | Forwarding committed intermediate request state. | Internal commits were replaced by flushes so `get_managed_session` owns one atomic commit/rollback boundary. | Failure/timeout tests assert no partial commit; 58 tests OK |
| WM-018 | Repeated downstream failures continued hammering a target. | Added a Neon-backed recent-failure threshold and structured `circuit_open` result. | Circuit-breaker query contract; 58 tests OK |
| WM-020 | Clients could not distinguish accepted from delivered. | Added an owned delivery-status endpoint exposing response and retry state. | `test_delivery_endpoint_exposes_client_confirmation_state`; 58 tests OK |
| WM-024 | Replay lookups lacked a matching compound index. | Added model and idempotent Neon compound index for replay dedupe fields. | Model plus migration contract; 58 tests OK |
| WM-025 | Summary counts were aggregated in Python. | Summary now uses SQL grouped/count expressions. | SQL query contract; 58 tests OK |
| WM-026 | Exports materialized all logs. | CSV/JSON exports now stream keyset-paginated rows; XLSX is capped. | `test_json_log_export_streams_keyset_pages`; 58 tests OK |
| WM-027 | Signature secrets looked indexable and their storage contract was unclear. | Secret remains encrypted, typed as text and deliberately has no database index. | Model metadata test; 58 tests OK |
| WM-028 | Cleanup paths performed local imports. | Shared imports were moved to module scope. | Import/source regression; 58 tests OK |
| WM-029 | Redirect success semantics were implicit. | Only 2xx is delivery success; 3xx is persisted as a forward failure. | Forward-status regression; 58 tests OK |
| WM-030 | Exact replay could not override query parameters. | Replay schema accepts bounded query overrides and composes the target URL safely. | Replay override test; 58 tests OK |
| WM-031 | Forward errors lost useful response context. | Structured reason code, status and sanitized detail are retained. | Downstream 500/timeout tests; 58 tests OK |
| WM-032 | Schema errors could be oversized and inconsistent. | Errors are normalized to bounded JSON-path messages. | Schema validation regression; 58 tests OK |
| WM-033 | Request export assumed absolute request paths. | Export URL construction safely resolves relative paths. | Export regression suite; 58 tests OK |
| WM-034 | Reading config created a default endpoint. | Config GET is read-only and returns an explicit empty contract. | Three read-only config tests; 58 tests OK |
| WM-035 | Anonymous ingestion ownership nullability was implicit. | `WebhookRequest.user_id` is explicitly nullable and indexed. | Model metadata test; 58 tests OK |
| WM-036 | Replay failures discarded downstream response bodies. | Sanitized bounded response detail is returned and persisted. | Replay 502 body test; 58 tests OK |
| WM-037 | HAR timestamps could end in duplicate UTC suffixes. | A single UTC formatter normalizes aware and naive datetimes. | HAR UTC test; 58 tests OK |
| WM-038 | Multiple Stripe timestamps were parsed ambiguously. | Ambiguous timestamp sets fail closed. | Multi-timestamp Stripe test; 58 tests OK |
| WM-039 | OpenAPI inference lost nested array item shape. | Recursive schema inference now describes nested arrays/objects. | Nested-array OpenAPI test; 58 tests OK |
| WM-040 | Corrupt stored method configuration could fail open. | Allowed methods are validated and invalid lists reject ingestion. | Stored-method fail-closed test; 58 tests OK |
| WM-041 | Diff serialization failed on dates/custom values. | Diff values use bounded JSON-safe conversion. | Non-JSON diff test; 58 tests OK |
| WM-042 | IP blacklist rejection had no operational trace. | Rejections emit a safe warning with endpoint/IP context. | Logging contract; 58 tests OK |
| WM-043 | Missing notification settings returned silently. | Missing settings now emit an operational warning. | `test_missing_notification_settings_emit_operational_warning`; 58 tests OK |
| WM-044 | Exports omitted schema-validation outcomes. | Export rows include normalized `schema_valid` and `schema_error`. | Streaming export test; 58 tests OK |
| WM-045 | Postman export omitted authentication metadata. | Generated collections include auth configuration. | Postman export regression; 58 tests OK |
| WM-046 | Mixed aware/naive values made comparisons unsafe. | Central UTC helpers normalize comparisons and output. | Timezone regression tests; 58 tests OK |
| WM-047 | Invalid backoff JSON silently used defaults. | Invalid configuration logs a warning before bounded fallback. | Backoff logging contract; 58 tests OK |
| WM-048 | Signature secrets accepted non-string values. | Provider signature config validates secret types before use. | Signature-type regression; 58 tests OK |
| WM-049 | Invalid PEM failures were opaque. | Safe diagnostic logging identifies invalid key configuration without leaking key material. | PEM failure regression; 58 tests OK |
| WM-050 | Replay references had no referential integrity. | Added self-referencing FK with `ON DELETE SET NULL` via idempotent Neon migration. | Model and migration contracts; 58 tests OK |
| WM-051 | Match paths rejected negative array indexes. | Path extraction supports Python-style negative positions with bounds checks. | Negative-index test; 58 tests OK |
| WM-052 | Authenticated cron endpoints had no abuse bound. | Added atomic per-job/per-minute Neon upsert limiter. | `test_cron_rate_limit_uses_atomic_neon_upsert`; 58 tests OK |
| WM-053 | Operators retried failures one by one. | Added owned batch-retry API with per-request eligibility results. | Batch retry test; 58 tests OK |
| WM-054 | Trend analytics were missing. | Added SQL daily total/failure analytics endpoint. | Analytics contract test; 58 tests OK |
| WM-055 | Binary payloads were not round-trippable. | Payload storage/serialization preserves binary content safely. | Binary round-trip test; 58 tests OK |
| WM-056 | Public API had no stable version namespace. | Added `/v1` aliases for ingestion, webhook and settings routers. | `test_v1_aliases_cover_ingestion_and_authenticated_webhook_routes`; 58 tests OK |
| WM-057 | Endpoint deletion destroyed state/history. | Delete now soft-deactivates the owned endpoint and retains logs. | Soft-delete test; 58 tests OK |
| WM-058 | Sensitive operator actions lacked attribution. | Added persisted Neon audit events for endpoint/retry mutations. | `test_audit_helper_persists_structured_event`; migration contract; 58 tests OK |
| WM-059 | Large exports had no asynchronous path. | Added scheduled export jobs in the durable outbox. | Scheduled-export test; 58 tests OK |
| WM-060 | Only one provider signature could be accepted. | Signature config accepts multiple candidates and succeeds if any valid signature matches. | Multiple-signature test; 58 tests OK |

### FeedbackLens Resolved Bugs

| ID | Root cause | What changed | Verification |
| --- | --- | --- | --- |
| FL-01 | Positive sentiment scoring branch was unreachable. | Corrected the scoring path and added positive-text regression coverage. | `python -m unittest tests.test_feedbacklens_production_pipeline tests.test_feedbacklens_dedupe_integration -v` |
| FL-02 | A global failure penalty ignored negation/context. | Failure scoring now respects negation and local problem context. | Focused FeedbackLens suites |
| FL-03 | Dedupe was a race-prone check before insert. | Added a partial Neon unique index for non-empty source message IDs and handles insert conflicts. | Focused FeedbackLens suites; migration contract test |
| FL-04 | Feedback text was interpolated directly into alert HTML. | All user-controlled alert fields are escaped at the email boundary. | Focused FeedbackLens suites |
| FL-06 | Normalization stripped non-ASCII customer text. | Unicode letters and language content are preserved. | Focused FeedbackLens suites |
| FL-07 | Any `login`/`sign-in` mention counted as a failure. | Those terms affect sentiment only near actual problem words. | Focused FeedbackLens suites |
| FL-08 | Source access/refresh tokens and webhook secrets were plaintext. | New source credentials are encrypted with required `ENCRYPTION_KEY`. | Focused FeedbackLens suites |
| FL-14 | Generic failure terms dominated sentiment too strongly. | Reduced the global penalty and made it context-aware. | Focused FeedbackLens suites |
| FL-19 | Synchronous email delivery blocked the event loop. | Email sending now runs through a worker thread. | Focused FeedbackLens suites |
| FL-20 | GitHub webhook verification accepted missing source secrets. | Missing secrets fail closed before payload processing. | Focused FeedbackLens suites |
| FL-23 | CSV imports accepted arbitrary upload content types. | Added explicit CSV media-type/filename validation. | Focused FeedbackLens suites |
| FL-25 | Truncation could fail on long text without spaces. | Added hard length bounding that remains safe for CJK/no-space input. | Focused FeedbackLens suites |
| FL-31 | Raw dictionaries could bypass entry validation. | Payload reconstruction now validates the core entry shape before ORM creation. | Focused FeedbackLens suites |
| FL-32 | Alert destination accepted malformed email values. | Settings updates use Pydantic email validation. | Focused FeedbackLens suites |
| FL-34 | Manually supplied source tokens bypassed encryption. | Manual source creation now uses the same encrypted credential path. | Focused FeedbackLens suites |
| FL-05 | Generic single terms were selected before compound topics. | Compound clusters such as `dark-mode`, CSV export and checkout crash are resolved first. | `test_compound_cluster_terms_win_over_generic_terms`; FeedbackLens 52 tests OK |
| FL-09 | Cluster requests rebuilt relationships with pairwise comparisons. | Entries persist `cluster_slug`; response construction is a single grouping pass and never invokes semantic pair matching. | `test_cluster_build_is_linear_and_uses_persisted_cluster_slug`; 52 tests OK |
| FL-10 | Each insert loaded up to 500 candidates. | Candidate lookup is bounded to a much smaller recent window with source/message prefilters. | `test_dedupe_candidate_query_is_bounded_well_below_legacy_500`; 52 tests OK |
| FL-11 | Bulk import repeated large candidate reads and pair comparisons. | Existing candidates load once and in-batch SimHash detects duplicates at bounded cost. | Bulk candidate and large-batch SimHash tests; 52 tests OK |
| FL-12 | Export materialized all feedback rows. | CSV export defers Neon reads to bounded streaming batches. | `test_csv_export_defers_database_reads_to_streaming_batches`; 52 tests OK |
| FL-13 | Transformer pipelines could initialize by default in the Render process. | Heavy local ML is explicit opt-in and has timeout fallback to deterministic enhanced keywords. | Opt-in and timeout tests; 52 tests OK |
| FL-15 | `updated_at` and `analyzed_at` were inferred from creation time. | Added real timezone-aware columns, processing updates and Neon backfill/migration. | Timestamp test plus migration contract; 52 tests OK |
| FL-16 | Priority helper carried an unreachable mention-count branch. | Removed the dead parameter/branch and bases priority on persisted analysis facts. | `test_priority_helper_has_no_dead_mention_count_parameter`; 52 tests OK |
| FL-17 | Text cleaning raised transport-layer HTTP exceptions. | Introduced a domain/business exception translated only at API boundaries. | `test_cleaning_raises_business_exception_instead_of_http_exception`; 52 tests OK |
| FL-18 | Source config and webhook payloads used ad-hoc dictionaries. | Added Pydantic validation for source configuration and GitHub webhook payload shape. | Source/GitHub schema tests; 52 tests OK |
| FL-21 | Public GitHub ingestion had no shared rate limit. | Counts completed persisted outbox rows in Neon before accepting more webhook work. | `test_public_webhook_rate_limit_uses_persisted_completed_outbox_rows`; 52 tests OK |
| FL-22 | Outbound integrations could follow unsafe hosts/redirect destinations. | Added public HTTP URL validation and final-target checks before provider requests. | `test_outbound_http_validation_rejects_ssrf_targets`; 52 tests OK |
| FL-24 | Feedback listing used offset-only pagination. | Added signed cursor encoding over `(created_at,id)` for stable pagination. | Cursor round-trip and list tests; 52 tests OK |
| FL-26 | Dedupe summary compared all possible pairs. | Added SimHash/prefix candidate prefiltering before semantic similarity. | `test_dedupe_summary_prefilters_pairs_before_semantic_similarity`; 52 tests OK |
| FL-27 | Spam vocabulary was hardcoded. | Spam terms and allowlist are configurable while retaining safe defaults. | `test_spam_terms_and_whitelist_are_configurable`; 52 tests OK |
| FL-28 | Domain phrases containing spam words were rejected without context. | Scoring now requires stronger contextual signals and honors the allowlist. | `test_contextual_spam_terms_do_not_reject_legitimate_domain_feedback`; 52 tests OK |
| FL-29 | Topic and urgent vocabularies were fixed in code. | Added `FEEDBACKLENS_TOPIC_TERMS` and `FEEDBACKLENS_URGENT_TERMS` overrides layered over defaults. | `test_topic_and_urgent_terms_are_configurable`; 52 tests OK |
| FL-30 | Draft replies were generic regardless of the reported area. | Drafts now include deterministic billing, access, data or integration-specific follow-up language. | `test_support_draft_is_topic_specific`; 52 tests OK |
| FL-33 | Expired Reddit/Twitter tokens left sources permanently failed. | Authorization failures now refresh and rotate encrypted OAuth tokens, persist them, then retry polling once. | `test_oauth_refresh_rotates_encrypted_source_token`; 52 tests OK |
| FL-35 | A hand-written suffix stripper produced inconsistent stems. | Replaced it with the maintained Snowball English stemmer while keeping Unicode-safe tokenization. | `test_feedback_stemmer_normalizes_common_inflections`; 52 tests OK |

### Cross-Project Resolution

| ID | Root cause | What changed | Verification |
| --- | --- | --- | --- |
| SKILL-01 | Repeated SaaS failures were reviewed ad hoc. | Created `saas-critical-hardening` with risk catalog, TDD workflow, deploy gate and audit reference. | `quick_validate.py`: valid; forward-test completed |

### FileCleaner Resolved Bugs

| ID | Root cause | What changed | Verification |
| --- | --- | --- | --- |
| FC-01 | `/files/utility` routed PDFs through the image converter, which rasterized every page and packaged the images as ZIP. | Added a PDF-specific cleanup path that removes document/XML metadata, compacts the PDF, verifies the output, preserves page count and returns `{name}.cleaned.pdf`. Original and cleaned files are persisted to R2 and tracked for cron cleanup. | RED: endpoint returned `application/zip`; GREEN: `test_pdf_utility_returns_multipage_pdf_and_persists_files_to_r2`; FileCleaner suite 15 tests OK |
