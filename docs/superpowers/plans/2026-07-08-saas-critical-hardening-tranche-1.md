# SaaS Critical Hardening Tranche 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the first security/revenue-risk tranche from the InvoiceFollow, WebhookMonitor, and FeedbackLens bug checklist with RED/GREEN tests.

**Architecture:** Keep changes scoped to pure helpers, validation models, and public endpoint guardrails. Avoid unrelated frontend or FileCleaner changes already present in the working tree.

**Tech Stack:** Python, FastAPI, SQLModel, unittest, Pydantic, cryptography/Fernet, Stripe webhook helpers, httpx.

---

### Task 1: InvoiceFollow Security And Validation Guardrails

**Files:**
- Modify: `tests/test_invoicefollow_production_pipeline.py`
- Modify: `apps/invoicefollow/backend/main.py`

- [ ] **Step 1: Write failing tests**

Add tests asserting:

```python
def test_invoicefollow_requires_encryption_key_and_uses_timezone_aware_now(self):
    invoice_main.IntegrationsCrypto._fernet = None
    with patch.dict(invoice_main.os.environ, {"ENCRYPTION_KEY": ""}, clear=False):
        with self.assertRaises(RuntimeError):
            invoice_main.IntegrationsCrypto.get_fernet()
    now = invoice_main._utc_now()
    self.assertIsNotNone(now.tzinfo)
    self.assertEqual(now.utcoffset(), timezone.utc.utcoffset(None))

def test_invoice_settings_notifications_are_opt_in(self):
    settings = invoice_main.InvoiceSettings(user_id=1)
    self.assertFalse(settings.weekly_digest_enabled)
    self.assertFalse(settings.immediate_alerts_enabled)

def test_reminder_schedule_uses_logs_for_done_status(self):
    schedule = invoice_main.build_reminder_schedule(
        due_date=date(2026, 6, 1),
        today=date(2026, 7, 16),
        user_name="Victor",
        logs=[SimpleNamespace(template_key="friendly", status="sent")],
    )
    statuses = {item["tone"]: item["status"] for item in schedule}
    self.assertEqual(statuses["neutral"], "pending")
    self.assertEqual(statuses["friendly"], "done")
    self.assertEqual(statuses["firm"], "pending")

def test_invoice_update_and_forward_detection_validate_corrupt_inputs(self):
    with self.assertRaises(Exception):
        invoice_main.InvoiceUpdate(amount=-10)
    with self.assertRaises(Exception):
        invoice_main.InvoiceUpdate(status="hacked")
    with self.assertRaises(Exception):
        invoice_main.InvoiceUpdate(currency="us dollar")
    with self.assertRaises(Exception):
        invoice_main.InvoiceEmailDetectRequest(
            sender_email="billing@example.test",
            source="forward",
            message_id="",
        )
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_invoicefollow_production_pipeline -v`

Expected: the new tests fail because the current code still allows fallback encryption, naive datetimes, opt-out notification defaults, elapsed-time schedule completion, and missing validators.

- [ ] **Step 3: Implement minimal code**

Change `IntegrationsCrypto.get_fernet`, `_utc_now`, `InvoiceSettings` defaults, `build_reminder_schedule`, `InvoiceUpdate`, and `InvoiceEmailDetectRequest` only.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.test_invoicefollow_production_pipeline -v`

Expected: all InvoiceFollow production pipeline tests pass.

### Task 2: InvoiceFollow Stripe Webhook Guardrail

**Files:**
- Modify: `tests/test_invoicefollow_production_pipeline.py`
- Modify: `apps/invoicefollow/backend/main.py`

- [ ] **Step 1: Write failing test**

Add:

```python
def test_stripe_webhook_rejects_unsigned_payload_when_secret_missing(self):
    session = _FakeSession(responses=[])
    with patch.dict(invoice_main.os.environ, {"STRIPE_WEBHOOK_SECRET": ""}, clear=False):
        response = _client(session).post(
            "/invoices/webhooks/stripe",
            json={"id": "evt_1", "type": "payment_intent.succeeded", "data": {"object": {"metadata": {}}}},
        )
    self.assertEqual(response.status_code, 500)
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_invoicefollow_production_pipeline.InvoiceFollowProductionPipelineTests.test_stripe_webhook_rejects_unsigned_payload_when_secret_missing -v`

Expected: FAIL because unsigned JSON is currently accepted.

- [ ] **Step 3: Implement minimal code**

Require `STRIPE_WEBHOOK_SECRET` and `Stripe-Signature`. Raise HTTP 500 when secret is missing and HTTP 400 when signature is missing/invalid.

- [ ] **Step 4: Update old webhook test to use a real signature**

Patch `stripe.Webhook.construct_event` in the old missing-invoice-id test so it still tests routing logic after signature verification.

- [ ] **Step 5: Run GREEN**

Run: `python -m unittest tests.test_invoicefollow_production_pipeline -v`

Expected: pass.

### Task 3: FeedbackLens Sentiment, Unicode, And Alert Safety

**Files:**
- Modify: `tests/test_feedbacklens_production_pipeline.py`
- Modify: `apps/feedbacklens/backend/main.py`

- [ ] **Step 1: Write failing tests**

Add tests asserting:

```python
def test_positive_feedback_with_negated_failure_stays_positive(self):
    analysis = feedback_main._analyze_feedback_locally("The login is not broken, it works great and feels reliable.")
    self.assertEqual(analysis["sentiment"], "positive")

def test_unicode_feedback_normalization_preserves_non_english_terms(self):
    normalized = feedback_main._normalize_feedback_text("crédito über 中文反馈")
    self.assertIn("crédito", normalized)
    self.assertIn("über", normalized)
    self.assertIn("中文反馈", normalized)

def test_urgent_feedback_alert_escapes_user_html(self):
    entry = feedback_main.FeedbackEntry(user_id=42, text="<img src=x onerror=alert(1)>", is_urgent=True, source="email")
    session = _FakeSession(responses=[[SimpleNamespace(alert_email="owner@example.test")]])
    asyncio.run(feedback_main._queue_urgent_feedback_alert(entry, session))
    html_body = session.added[0].payload["html_body"]
    self.assertIn("&lt;img", html_body)
    self.assertNotIn("<img src=x", html_body)
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_feedbacklens_production_pipeline -v`

Expected: new tests fail on global failure scoring, ASCII-stripping normalization, and unescaped alert preview.

- [ ] **Step 3: Implement minimal code**

Remove global failure penalty, make failure scoring context-aware for login/sign-in, keep Unicode letters/numbers in normalization, and escape HTML fields in alert email.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.test_feedbacklens_production_pipeline -v`

Expected: pass.

### Task 4: WebhookMonitor Forwarding Failure Semantics And Health

**Files:**
- Modify: `tests/test_webhook_spec_completion.py`
- Modify: `apps/webhookmonitor/backend/main.py`

- [ ] **Step 1: Write failing tests**

Add tests asserting `process_webhook_forward` returns `{"status": "failed"}` rather than raising on downstream 500, preserves `content-type`, and that `/webhooks/health` returns status.

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_webhook_spec_completion -v`

Expected: new forwarding failure test fails because the job raises `Exception(req.forward_error)`.

- [ ] **Step 3: Implement minimal code**

Return failed payloads instead of raising for business failures, keep `Content-Type` in safe headers, and add a health route.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.test_webhook_spec_completion -v`

Expected: pass.

### Task 5: Docs And Checklist Update

**Files:**
- Modify: `docs/qa/2026-07-08-invoice-webhook-feedback-bug-checklist.md`

- [ ] **Step 1: Mark completed IDs from tranche 1**

Mark the verified IDs as `[x]` and leave broader distributed/DB/deploy items pending.

- [ ] **Step 2: Run diff check**

Run: `git diff --check`

Expected: no whitespace errors beyond pre-existing CRLF warnings.
