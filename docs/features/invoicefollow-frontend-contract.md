# InvoiceFollow Frontend Contract

This contract covers the production InvoiceFollow dashboard, API clients, and CLI.

## Product Boundary

- InvoiceFollow tracks existing invoices and automates collection follow-up.
- Manual form tracks existing invoices only. It does not issue, generate, render, or certify a legal invoice.
- AI is not part of InvoiceFollow. Reply classification is deterministic and conservative; ambiguous or negated payment wording goes to manual review.
- Reminder copy comes from editable templates with fixed variables.

## Ingestion

- `POST /connect/gmail` starts Gmail OAuth with `gmail.readonly` and `gmail.send`; it does not mark the account connected until callback success.
- `GET /connect/gmail/callback` exchanges the OAuth code for tokens and stores the connected account.
- `POST /connect/outlook` starts Microsoft Graph OAuth with `Mail.Read`, `Mail.Send`, and `offline_access`; it does not mark the account connected until callback success.
- `GET /connect/outlook/callback` exchanges the OAuth code for tokens and stores the connected account.
- Forward fallback address is returned by `GET /settings` as `forward_address`.
- `POST /invoices/detect-email` accepts `subject`, `body`, `sender_email`, `sender_name`, `message_id`, and `source`.
- Detection returns a preview with `client_name`, `client_email`, `amount`, `currency`, `invoice_number`, `due_date`, `issued_date`, `confidence`, `draft_id`, and `requires_user_confirmation`.
- `POST /invoices/drafts/{draft_id}/confirm` creates a tracking record after the user edits or confirms detected fields.
- `POST /invoices` creates a manual tracking record for an existing invoice from WhatsApp, PDF, or offline sending.
- `POST /invoices/import-csv` imports existing invoice records from CSV/XLS/XLSX.

## Invoice Dashboard

- `GET /invoices` lists invoices for the user.
- `GET /invoices/{id}` returns the full invoice detail.
- `PUT /invoices/{id}` edits the tracking record.
- `POST /invoices/{id}/pause` pauses the sequence.
- `POST /invoices/{id}/resume` resumes the sequence.
- `POST /invoices/{id}/mark-paid` marks the invoice paid.
- `GET /invoices/{id}/timeline` returns the visual schedule, emails sent, replies, payments, and notes.
- Main table columns: client, amount/currency, due date, days overdue, state, next step, actions.

## Templates

- `GET /templates` returns `original`, `friendly`, `firm`, `urgent`, and `pause` templates.
- `PUT /templates/{id}` updates one template.
- Variables: `{client_name}`, `{invoice_number}`, `{amount}`, `{currency}`, `{due_date}`, `{days_overdue}`, `{company_name}`, `{user_name}`.
- UI should preview rendered variables and allow disabling individual steps.

## Settings And Payments

- `GET /settings` and `PUT /settings` manage company name, sender name, send hour, timezone, weekend policy, no-send-after hour, weekly digest, and immediate alerts.
- `POST /connect/stripe` requires a restricted read-only Stripe key, stores it server-side, and enables matching by `metadata.invoice_id` or amount/email fallback.
- `POST /connect/paypal` requires read-only PayPal client credentials and enables amount/email matching.
- Free users cannot connect Stripe or PayPal.

## Metrics And Digest

- `GET /metrics` returns recovery rate, recovered/pending amounts, average payment time, and at-risk count.
- `GET /digest` generates the weekly digest preview used for Monday 9am delivery.
- Cron endpoints enqueue reminders, poll Gmail/Outlook replies, poll Stripe/PayPal payments, and the shared `/worker/process` endpoint consumes `SystemOutbox` jobs with retry/backoff.

## Frontend Copy Guardrails

- Do not say "generate invoice" or "issue invoice".
- Do not expose `/ai-tone`.
- Do not mention AI or model-generated tone for InvoiceFollow.
- Use "Track existing invoice", "Import existing invoice records", and "Add existing invoice record".
