# Critical Hardening Report

Started: 2026-07-08
Last updated: 2026-07-11

Scope:
- InvoiceFollow bug list from goal objective.
- WebhookMonitor bug list from goal objective.
- FeedbackLens bug list from goal objective.
- Cross-project prevention skill.
- FileCleaner PDF regression reported during execution.

## Confirmed Runtime Architecture

- Neon Postgres stores application data, idempotency, rate limits, audit records and the durable outbox.
- Render hosts `backend_core.universal_main`.
- Vercel hosts the product frontends.
- Authenticated cron jobs enqueue and process periodic/outbox work.
- Polar handles DevForge subscriptions and product access.
- Stripe handles InvoiceFollow payment reconciliation.
- Cloudflare R2 stores FileCleaner user inputs and outputs; cron cleanup removes expired objects.
- PayPal and Redis are not part of the target architecture.

## Verification Log

- `python -m unittest tests.test_invoicefollow_production_pipeline -v`: 31 tests OK.
- `python -m unittest tests.test_feedbacklens_production_pipeline tests.test_feedbacklens_dedupe_integration -v`: 22 tests OK.
- `python -m unittest tests.test_webhook_spec_completion -v`: 11 tests OK.
- After tranche 2:
  - `python -m unittest tests.test_invoicefollow_production_pipeline -v`: 40 tests OK.
  - `python -m unittest tests.test_feedbacklens_production_pipeline tests.test_feedbacklens_dedupe_integration -v`: 31 tests OK.
  - `python -m unittest tests.test_webhook_spec_completion tests.test_webhook_monitor_moat -v`: 27 tests OK.
- Skill validation: `python C:\Users\victor\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\victor\.agents\skills\saas-critical-hardening`: valid.
- Skill forward-test: subagent converted a fictional SaaS snippet into actionable hardening IDs using the skill.
- Latest focused suites:
  - InvoiceFollow: 54 tests OK.
  - FeedbackLens plus dedupe integration: 52 tests OK.
  - WebhookMonitor plus moat: 35 tests OK before final low-risk tranche.
  - FileCleaner production pipeline: 15 tests OK, including multipage PDF/R2 regression.
  - Deploy configuration contract: 4 tests OK.
  - Neon migration contract: OK; migrations applied successfully to Neon on 2026-07-10.
- Final closure gate (2026-07-11):
  - `python -m unittest discover -s tests -q`: 331 tests OK after live cron timezone regression coverage.
  - `pnpm run typecheck`: 8/8 tasks OK.
  - `pnpm run lint`: 9/9 tasks OK.
  - Python compile, universal backend import and `git diff --check`: OK.
  - Neon verified `webhook_audit_logs`, `webhook_cron_rate_limits`, replay FK and compound replay index.

## Tranche 1 Fixes

### InvoiceFollow

- IF-01: Removed public hardcoded encryption fallback. `ENCRYPTION_KEY` is now required for integration crypto.
- IF-03: Stripe webhook now fails closed when `STRIPE_WEBHOOK_SECRET` or `Stripe-Signature` is missing.
- IF-05: `_utc_now()` now returns timezone-aware UTC datetimes.
- IF-10: Reminder schedule `done` states now come from reminder logs, not elapsed overdue days.
- IF-15: `InvoiceUpdate` validates amount, status, and currency.
- IF-20: Forwarded invoice email detection requires `message_id`.
- IF-29/IF-30: Weekly digest and immediate alerts default to opt-in false.

### WebhookMonitor

- WM-001: Integration crypto cache is lock-protected and returns an immutable tuple.
- WM-004: Downstream 4xx/5xx forwarding failures return structured failed payloads instead of generic exceptions.
- WM-007: Added `/webhooks/health`.
- WM-017: Added regression coverage that forwarding preserves safe headers including `Content-Type`.

### FeedbackLens

- FL-01: Positive sentiment branch is covered by tests.
- FL-02/FL-14: Removed global failure penalty that ignored negation.
- FL-04: Urgent alert HTML escapes user-controlled text.
- FL-06: Feedback normalization preserves Unicode text.
- FL-07: `login` and `sign-in` only count as failure near problem terms.

## Common Root Causes

- Fail-open security defaults: webhooks and encryption accepted unsafe missing configuration.
- Inferred state instead of persisted truth: UI schedule status treated elapsed days as completed work.
- In-process guarantees for distributed problems: rate limits, dedupe, and cron safety need Neon/idempotency backing.
- User-controlled text crossing trust boundaries: HTML email rendering needed escaping.
- Naive time handling: UTC values must stay timezone-aware until display/localization edges.
- Unbounded work: exports, polling, and retry loops need pagination, batch caps, or streaming.

## Tranche 2 Fixes

### InvoiceFollow

- IF-04: Added per-user per-minute reminder email guard.
- IF-07/IF-08: Added model-level uniqueness for promise tokens and reply provider message IDs.
- IF-13: Marked not applicable and removed from the supported surface; DevForge uses Polar subscriptions and Stripe invoice reconciliation.
- IF-16: Promise links are idempotent, expiring at 30 days, and store `promise_used_at`.
- IF-18: Sender company fallback now returns `Unknown`.
- IF-19: Payment polling metrics count matched payments, not scanned provider events.
- IF-21: Invalid send windows fail safe.
- IF-23: Gmail OAuth state is cleared after a successful callback.

### WebhookMonitor

- WM-002: Ingestion now queues a durable `SystemOutbox` forwarding job before returning received.
- WM-003: Added provider event idempotency model/helper.
- WM-006/WM-012/WM-015: Log/search/event endpoints support pagination and SQL-side status filters.
- WM-008: Added metrics endpoint.
- WM-011: Scheduled retry processing is batch-limited.
- WM-016: Successful requests cannot be retried.
- WM-022: Chunked body size limit is covered.
- WM-023: Endpoint deletion verifies ownership before deleting requests.

### FeedbackLens

- FL-03: Added non-empty source-message unique index and duplicate conflict handling.
- FL-08/FL-34: New source access, refresh, and webhook secrets are encrypted with required `ENCRYPTION_KEY`.
- FL-19: Email sending runs off the event loop.
- FL-20: GitHub webhooks reject missing source secrets.
- FL-23: CSV upload content type is validated.
- FL-25: Long text truncation works without spaces.
- FL-31: Payload-to-entry reconstruction validates core shape.
- FL-32: Alert email input is validated.

## Prevention Skill

Created and validated:
- `C:\Users\victor\.agents\skills\saas-critical-hardening\SKILL.md`
- `C:\Users\victor\.agents\skills\saas-critical-hardening\references\audit-checklist.md`

Purpose:
- Trigger before SaaS launch/deploy/payment/webhook/security work.
- Converts risks into IDs, TDD checks, deploy gates, and residual infrastructure risks.

## Final Closure

- Checklist result: 127 resolved, 1 not applicable, 0 pending.
- The prevention skill is installed and validated.
- All repository and Neon gates pass; deployment/live verification is recorded after the release commit.

## External Configuration Residual

- Render now has a generated `ENCRYPTION_KEY`; Neon was checked first and contained no stored integration secrets requiring legacy re-encryption.
- Real Stripe invoice reconciliation remains fail-closed until `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` are supplied in Render. No usable credentials were present locally or in Render, so they were not fabricated.

## Product Behavior: Before vs Current

### FileCleaner

Before: mainly cleaned CSV/XLSX data, while generic file-utility promises were incomplete; sending a PDF through the utility route rasterized each page and returned a ZIP of images.

Current: keeps the tabular cleaning pipeline, background outbox jobs, previews, retries and deep-clean controls. Image utilities remove metadata/convert formats, and PDF utility now returns one compact valid `.cleaned.pdf`, preserving page count. Original and cleaned artifacts are stored in R2 and tracked for cron cleanup.

### InvoiceFollow

Before: created tracking records, sent overdue reminders, handled promises and exported invoices, but relied on process-local limits, non-atomic capacity checks, unbounded provider reads and inferred schedule state.

Current: tracks receivables rather than issuing legal invoices; imports/detects invoices, schedules reminders, handles Gmail replies, reconciles Stripe payments, records promises and exports data. Neon now provides public rate limits, cron/capacity locks, uniqueness and audit trails; provider/export work is paged or bounded, links expire, and UI status comes from persisted facts. PayPal was removed from the supported surface.

### PriceTrackr

Before: created URL trackers, scraped price/stock, stored history, scheduled checks, alerted and exported.

Current: retains that core plus prior production hardening already present in the repository: plan limits, safer URL handling, same-origin frontend routes, pending-state confirmation, soft-delete/history controls and operational scrape records. This goal did not materially alter PriceTrackr.

### WebhookMonitor

Before: accepted public webhooks, listed logs, forwarded requests and retried failures, but delivery could be lost after HTTP 200 and observability/idempotency/pagination were incomplete.

Current: persists the event and durable forwarding job before acknowledgement, deduplicates provider events in Neon, validates signatures/schema/IP policy, paginates and filters logs, exposes health/metrics/analytics, classifies network failures, batches retries/cleanup, streams exports, records audits, rate-limits cron jobs in Neon, supports `/v1` aliases and protects secrets with a required encryption key.

### FeedbackLens

Before: accepted manual/CSV feedback, ran sentiment/urgency analysis, drafted generic replies, sent digests and exported, but source integrations, dedupe, clustering and dashboard decision data were limited.

Current: ingests manual, CSV, email, GitHub, Reddit and Twitter/X sources; encrypts credentials; refreshes OAuth; validates webhooks/config; rate-limits public ingestion; performs bounded atomic dedupe and linear persisted clustering; streams exports; records real analysis timestamps; produces topic-specific drafts; and uses deterministic local analysis by default with heavy ML as explicit opt-in.
