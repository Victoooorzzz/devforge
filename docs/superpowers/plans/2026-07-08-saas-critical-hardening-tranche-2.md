# SaaS Critical Hardening Tranche 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close additional high-impact bugs that can be fixed locally without adding new external infrastructure.

**Architecture:** Keep one worker per product. Use Neon constraints, advisory locks and persisted outbox/rate-limit records for distributed guarantees; do not add Redis or another service.

**Tech Stack:** Python, FastAPI, SQLModel, Pydantic, unittest, httpx.

---

### Task 1: InvoiceFollow Operational Correctness

**Files:**
- Modify: `apps/invoicefollow/backend/main.py`
- Modify: `tests/test_invoicefollow_production_pipeline.py`

Targets:
- IF-04: per-user per-minute email send guard in reminder enqueue path.
- IF-07: model-level unique constraint for `promise_token`.
- IF-08: model-level unique compound constraint for reply events.
- IF-13: mark PayPal not applicable; subscriptions use Polar and invoice reconciliation uses Stripe.
- IF-16: idempotent and expiring public promise links with persisted `promise_used_at`.
- IF-18: `_sender_company` returns `"Unknown"` fallback.
- IF-19: payment poll `processed_payments` counts matches, not scanned events.
- IF-21: `is_time_to_send` fails safe on invalid send windows.
- IF-23: Gmail OAuth state is invalidated after successful callback.

TDD:
- Add focused tests for each behavior before production edits.
- Run `python -m unittest tests.test_invoicefollow_production_pipeline -v`.

### Task 2: FeedbackLens Storage, Ingestion, And Email Safety

**Files:**
- Modify: `apps/feedbacklens/backend/main.py`
- Modify: `tests/test_feedbacklens_production_pipeline.py`
- Modify: `tests/test_feedbacklens_dedupe_integration.py` only if needed.

Targets:
- FL-03: model-level unique constraint for `(user_id, source, source_message_id)`.
- FL-08/FL-34: encrypt source tokens/webhook secrets at rest using an env-required crypto helper.
- FL-19: run sync email sending off event loop in `handle_feedback_email`.
- FL-20: reject GitHub webhooks if source secret is missing.
- FL-23: validate CSV upload content type.
- FL-25: truncate long feedback safely even without spaces.
- FL-31: validate payload-to-entry reconstruction enough to avoid raw invalid dicts.
- FL-32: validate alert email format for settings/model boundary where available.

TDD:
- Add focused tests first.
- Run `python -m unittest tests.test_feedbacklens_production_pipeline tests.test_feedbacklens_dedupe_integration -v`.

### Task 3: WebhookMonitor Ingestion, Pagination, And Retry Safety

**Files:**
- Modify: `apps/webhookmonitor/backend/main.py`
- Modify: `tests/test_webhook_spec_completion.py`
- Modify: `tests/test_webhook_monitor_moat.py` only if needed.

Targets:
- WM-002: ingestion must enqueue/persist durable forwarding job before returning success, not rely only on `BackgroundTasks`.
- WM-003: add model-level idempotency helper/table or deterministic duplicate guard for provider event IDs where available from headers/body.
- WM-006/WM-012/WM-015: add real offset/limit pagination and avoid filtering after SQL limit where practical.
- WM-008: add simple metrics endpoint based on DB aggregates/counts.
- WM-011: bound scheduled retry batch size.
- WM-016: prevent retrying successful requests.
- WM-022: preserve body-size enforcement for chunked streams.
- WM-023: verify endpoint ownership before deleting associated requests.

TDD:
- Add focused tests first.
- Run `python -m unittest tests.test_webhook_spec_completion tests.test_webhook_monitor_moat -v`.
