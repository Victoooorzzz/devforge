# 🚀 DevForge — Production Setup Guide

Complete guide to configure all environment variables, DNS, and third-party services
for deploying the DevForge monorepo to Vercel (free tier).

---

## 📋 Required Environment Variables

Set these in **Vercel → Project Settings → Environment Variables** (or in a `.env` file for local development).

### 🔐 Core / Auth
| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | Neon PostgreSQL connection string (use pooled URL for serverless) | `postgresql+asyncpg://user:pass@ep-xxx.neon.tech/neondb?sslmode=require` |
| `SECRET_KEY` | JWT signing key — generate with `openssl rand -hex 32` | `3f7e9...` |
| `CRON_SECRET` | Shared secret to protect all `/cron/*` endpoints | `your-random-secret-here` |
| `ADMIN_SECRET` | Secret to access `/admin/stats` — use `X-Admin-Key` header | `admin-secret-here` |

### 🤖 AI (FeedbackLens)
| Variable | Description | Notes |
|---|---|---|
| `GEMINI_API_KEY` | Your Google Gemini API key | Free tier: 15 requests/min, 1500/day. Get it at [ai.google.dev](https://ai.google.dev) |

> **No user API key required.** The platform uses this key server-side. If quota is exceeded, VADER (offline) takes over automatically.

### 📧 Email (Resend)
| Variable | Description | Example |
|---|---|---|
| `RESEND_API_KEY` | Resend API key for transactional emails | `re_xxxxxxxxxxxx` |
| `RESEND_FROM_EMAIL` | Verified sender email address | `noreply@devforgeapp.pro` |

### 💾 File Storage (Cloudflare R2)
| Variable | Description |
|---|---|
| `R2_ENDPOINT_URL` | R2 endpoint — `https://<account-id>.r2.cloudflarestorage.com` |
| `AWS_ACCESS_KEY_ID` | R2 API Token (Access Key ID) |
| `AWS_SECRET_ACCESS_KEY` | R2 API Token (Secret) |
| `R2_BUCKET_NAME` | Your R2 bucket name (e.g., `devforge-files`) |

### 💳 Payments (LemonSqueezy)
| Variable | Description |
|---|---|
| `LEMONSQUEEZY_API_KEY` | Your LemonSqueezy API key |
| `LEMONSQUEEZY_STORE_ID` | Your store ID from LemonSqueezy dashboard |
| `LEMONSQUEEZY_WEBHOOK_SECRET` | Webhook signing secret — find in LemonSqueezy → Settings → Webhooks |

---

## 📧 Setting Up Resend (DKIM/SPF) — Anti-Spam

Without DKIM/SPF, your reminder emails will land in spam. Follow these steps:

### Step 1: Add your domain to Resend
1. Go to [resend.com/domains](https://resend.com/domains)
2. Click **Add Domain** → enter `devforgeapp.pro`
3. Resend shows you 3 DNS records to add

### Step 2: Add DNS records in Cloudflare
In Cloudflare DNS → Add the following records:

```
# SPF record (allows Resend to send as you)
Type: TXT
Name: @
Value: v=spf1 include:amazonses.com ~all

# DKIM record (Resend provides the exact value)
Type: TXT  
Name: resend._domainkey
Value: [Provided by Resend — copy-paste it exactly]

# DMARC (optional but recommended)
Type: TXT
Name: _dmarc
Value: v=DMARC1; p=none; rua=mailto:dmarc@devforgeapp.pro
```

### Step 3: Verify in Resend
- Wait 5-10 minutes after adding DNS records
- Click **Verify** in Resend dashboard
- Status should show ✅ Verified

---

## ⏰ Vercel Cron Jobs

The `vercel.json` already defines all scheduled tasks. They run automatically after deployment.

| Cron Path | Schedule | Task |
|---|---|---|
| `/api/trackers/cron/update` | Every hour | PriceTrackr: check prices (filters by `next_check_at`) |
| `/api/invoices/cron/reminders` | Daily 9am UTC | InvoiceFollow: send overdue reminders |
| `/api/feedback/cron/summary` | Monday 8am UTC | FeedbackLens: send weekly digest |
| `/api/webhooks/cron/silence` | Every 15 min | WebhookMonitor: silence detection |
| `/api/webhooks/cron/process-retries` | Every 5 min | WebhookMonitor: exponential backoff retries |
| `/api/webhooks/cron/cleanup` | 1st of each month | WebhookMonitor: delete logs > 30 days |

> **Important:** All cron requests include `Authorization: Bearer $CRON_SECRET` header automatically (Vercel handles this). Set the same value in your Vercel env vars.

---

## 🗄️ Database Migrations (Neon)

Run these SQL commands in the Neon console after deploying for the first time:

```sql
-- FileCleaner new columns
ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS job_status VARCHAR DEFAULT 'queued';
ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS error_message VARCHAR;

-- PriceTrackr new columns
ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS check_frequency_hours INTEGER DEFAULT 24;
ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS next_check_at TIMESTAMP WITH TIME ZONE;

-- WebhookMonitor new columns
ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;
ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS last_retry_status INTEGER;
ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS auto_retry_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS auto_retry_enabled BOOLEAN DEFAULT FALSE;

-- FeedbackLens new columns
ALTER TABLE feedback_entries ADD COLUMN IF NOT EXISTS analysis_engine VARCHAR;
ALTER TABLE feedback_settings ADD COLUMN IF NOT EXISTS alert_email VARCHAR DEFAULT '';
ALTER TABLE feedback_settings ADD COLUMN IF NOT EXISTS weekly_summary_enabled BOOLEAN DEFAULT TRUE;
```

---

## 🔗 LemonSqueezy Webhook Setup

For InvoiceFollow auto-pause when a payment is received:

1. Go to [LemonSqueezy Dashboard → Settings → Webhooks](https://app.lemonsqueezy.com/settings/webhooks)
2. Add a new webhook:
   - **URL**: `https://api.devforgeapp.pro/invoices/webhooks/lemonsqueezy`
   - **Events**: `order_created`
   - Copy the **Signing Secret** → add it as `LEMONSQUEEZY_WEBHOOK_SECRET` in Vercel
3. When creating a payment link for invoices, include `custom_data[invoice_id]` in the metadata

---

## 🛡️ Admin Dashboard

Access the unified stats endpoint:

```bash
curl -H "X-Admin-Key: your-admin-secret" \
  https://api.devforgeapp.pro/admin/stats
```

Or open the admin page at `https://feedbacklens.devforgeapp.pro/admin` (if you build the Next.js admin UI).

---

## 📈 Scaling Beyond Free Tier

When you start exceeding limits, upgrade in this order:

| When | Problem | Solution |
|---|---|---|
| > 100 users | Neon 500MB limit | Upgrade Neon to $19/mo (10GB) |
| > 50MB files | FileCleaner timeouts | Add Upstash Redis queue ($0 up to 10k/day) |
| Price scraping blocks | IP blocked | Add ScrapingBee ($0.001/request, pay-as-you-go) |
| > 3000 emails/mo | Resend free limit | Upgrade Resend to $20/mo (100k emails) |
| > 100GB storage | R2 limit | Already $0.015/GB after 10GB (very cheap) |

---

## 🧪 Testing Your Setup

```bash
# Test cron manually (replace with your actual domain and secret)
curl -X POST https://api.devforgeapp.pro/api/trackers/cron/update \
  -H "Authorization: Bearer your-cron-secret"

# Test admin endpoint
curl https://api.devforgeapp.pro/admin/stats \
  -H "X-Admin-Key: your-admin-secret"

# Test LemonSqueezy webhook (simulate)
curl -X POST https://api.devforgeapp.pro/invoices/webhooks/lemonsqueezy \
  -H "Content-Type: application/json" \
  -d '{"meta":{"event_name":"order_created","custom_data":{"invoice_id":"42"}}}'
```
