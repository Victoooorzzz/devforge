# InvoiceFollow Production Pipeline

## Scope

InvoiceFollow is a recovery workflow for invoices that already exist outside the product. It ingests invoice records from Gmail, Outlook, forwarded email, CSV/XLS/XLSX, or a safe manual tracking form.

## Backend Features Implemented

1. Email detection parses client, amount, currency, invoice number, due date, and issued date from invoice-like emails.
2. Detected invoices become drafts and require user confirmation before tracking starts.
3. Manual form creates a tracking record only; it does not create legal invoice documents.
4. Reminder sequence supports days 0, 7, 15, 30, and 45 pause with sender escalation.
5. Templates are editable through `/templates` and `/templates/{id}` with variable preview support.
6. Reply intent classification is deterministic, handles negated/attributed payment wording conservatively, and returns `[PAGADO]`, `[EXCUSA_VALIDA]`, `[EXCUSA_FALSA]`, or `[DESCONOCIDO]`.
7. Reply actions pause, resume, flag, or mark paid only when a real payment is confirmed.
8. Stripe detection matches `payment_intent.succeeded` by `metadata.invoice_id`, then amount/email fallback.
9. PayPal detection matches completed payments by amount, currency, and payer email.
10. Weekly digest groups payments, valid excuses, reminders, at-risk invoices, and monthly recovery totals.
11. Gmail/Outlook OAuth callbacks exchange authorization codes for tokens before an account is marked connected.
12. The shared worker consumes `SystemOutbox` send jobs; InvoiceFollow sends through Gmail/Outlook when connected and falls back to Resend.
13. Cron endpoints perform real reply polling and payment polling instead of returning readiness placeholders.

## API Surface

- `GET /invoices`
- `POST /invoices`
- `GET /invoices/{id}`
- `PUT /invoices/{id}`
- `POST /invoices/{id}/pause`
- `POST /invoices/{id}/resume`
- `POST /invoices/{id}/mark-paid`
- `GET /invoices/{id}/timeline`
- `POST /invoices/detect-email`
- `POST /invoices/drafts/{draft_id}/confirm`
- `GET /templates`
- `PUT /templates/{id}`
- `POST /connect/gmail`
- `GET /connect/gmail/callback`
- `POST /connect/outlook`
- `GET /connect/outlook/callback`
- `POST /connect/stripe`
- `POST /connect/paypal`
- `GET /metrics`
- `GET /digest`
- `GET/PUT /settings`

## Plan Limits

- Free: 5 active invoices, 25 emails/month, 10 reply classifications/month, Gmail only, no API, no digest.
- Pro: 50 active invoices, 500 emails/month, 200 reply classifications/month, Gmail + Outlook, Stripe read-only, API, custom templates, weekly digest.
- Team: 200 active invoices, 2,000 emails/month, 1,000 reply classifications/month, Stripe + PayPal, 5 users, Slack-ready alerts, priority support.

## Frontend Implementation Notes

- Dashboard should show active invoices, delay days, next step, status, and row actions.
- Detail view should use `/invoices/{id}/timeline`.
- Settings should expose Gmail/Outlook/Stripe/PayPal connection actions, sender config, send windows, and notification toggles.
- Templates screen can live in settings as long as it supports edit, preview, and step enable/disable.
- AI and generated tone are not features in this product.
