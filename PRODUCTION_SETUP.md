# DevForge Production Setup

This monorepo deploys five micro-SaaS products with a shared Render backend, Vercel frontends, Polar payments, Neon/Postgres, and cron-job.org for scheduled work.

## Core Environment

Set these in Render for `devforge-universal-backend`:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Async Postgres URL for Neon/Render Postgres. |
| `JWT_SECRET` | JWT signing secret. |
| `FRONTEND_URL` | Main frontend URL, for example `https://devforgeapp.pro`. |
| `ALLOWED_ORIGINS` | Comma-separated frontend origins for all five products. |
| `CRON_SECRET` | Bearer token shared with cron-job.org. |
| `ADMIN_SECRET` | Secret for `/admin/stats` via `X-Admin-Key`. |

## Payments (Polar)

Set these in Render:

| Variable | Purpose |
|---|---|
| `POLAR_ACCESS_TOKEN` | Polar organization access token used server-side. |
| `POLAR_WEBHOOK_SECRET` | Polar webhook signing secret. |
| `POLAR_PRODUCT_ID_FILECLEANER` | FileCleaner product ID. |
| `POLAR_PRODUCT_ID_INVOICEFOLLOW` | InvoiceFollow product ID. |
| `POLAR_PRODUCT_ID_PRICETRACKR` | PriceTrackr product ID. |
| `POLAR_PRODUCT_ID_WEBHOOKMONITOR` | WebhookMonitor product ID. |
| `POLAR_PRODUCT_ID_FEEDBACKLENS` | FeedbackLens product ID. |

The backend maps `app_name` to a configured product ID server-side. Do not trust product IDs sent directly from the client.

## Polar Webhook

Create one Polar webhook:

| Setting | Value |
|---|---|
| URL | `https://devforge-universal-backend.onrender.com/webhooks/polar` |
| Events | Checkout, order, and subscription lifecycle events |
| Secret env var | `POLAR_WEBHOOK_SECRET` |

The webhook stores access per product in `user_product_access`, so paying for one app only unlocks that app.

## Cron Jobs (cron-job.org)

Production scheduled work depends on cron-job.org, not Vercel Cron.

Add these jobs in cron-job.org and send `Authorization: Bearer <CRON_SECRET>`:

| Method | URL | Schedule | Purpose |
|---|---|---|---|
| `POST` | `https://devforge-universal-backend.onrender.com/worker/enqueue-periodic` | Every hour | Enqueue due work for all five products and process one worker cycle. |
| `POST` | `https://devforge-universal-backend.onrender.com/worker/process` | Every 5 minutes | Drain pending `system_outbox` jobs. |
| `POST` | `https://devforge-universal-backend.onrender.com/worker/cleanup` | Daily | Remove old completed or failed jobs. |

App-specific cron routes can stay as diagnostics, but production should use the worker routes above.

## Database Migrations

The backend runs lightweight startup migrations in `packages/backend_core/db_migrations.py` after `SQLModel.metadata.create_all`.

For future risky schema changes, add intentional migration statements there or move to a full migration tool before deployment.

## Product Dependencies

Render installs from the root `requirements.txt`. Keep production-only packages there, including:

| Package | Used by |
|---|---|
| `vaderSentiment` | FeedbackLens fallback analysis. |
| `thefuzz[speedup]` | FileCleaner fuzzy duplicate checks. |
| `boto3` | FileCleaner R2/S3 storage. |
| `google-genai` | AI features. |

## Manual Checks

```bash
curl -X POST https://devforge-universal-backend.onrender.com/worker/enqueue-periodic \
  -H "Authorization: Bearer your-cron-secret"

curl -X POST https://devforge-universal-backend.onrender.com/worker/process \
  -H "Authorization: Bearer your-cron-secret"

curl https://devforge-universal-backend.onrender.com/admin/stats \
  -H "X-Admin-Key: your-admin-secret"
```
