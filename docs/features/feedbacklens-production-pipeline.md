# FeedbackLens Production Pipeline

## Scope

FeedbackLens turns raw feedback into a triage dashboard without external generation services. The core path is collection, cleanup, Local sentiment analysis, theme extraction, near-duplicate detection, weekly summary, export, and reply drafting.

## Collection

- Manual textarea creates one feedback item.
- Bulk textarea imports one item per line through the same cleanup, dedupe, local analysis, clustering, priority, and urgent-alert path as single feedback.
- CSV upload imports up to 500 rows from the `text` column through the same production path.
- `/sources` stores source configuration for Twitter/X, Reddit, GitHub Issues, Canny, email forwarding, and manual entry.
- `DELETE /sources/{id}` disconnects a source, clears stored tokens/secrets, and keeps historical feedback for dashboards and exports.
- `/feedback/ingest/email` receives parsed forwarded email feedback and includes text-like attachments sent by the inbound email provider.
- `/feedback/ingest/canny` receives Canny webhook feedback.
- `/feedback/ingest/github` receives signed GitHub Issues webhooks.
- GitHub OAuth starts at `/connect/github` and completes at `/connect/github/callback`; issue creation uses the configured GitHub source token and repo.
- Twitter/X OAuth starts at `/connect/twitter` and completes at `/connect/twitter/callback` with PKCE.
- Reddit OAuth starts at `/connect/reddit` and completes at `/connect/reddit/callback`.
- `/feedback/cron/poll` polls due Twitter/X, Reddit, and GitHub sources and ingests new items through the same cleanup/dedupe path.
- The unified `/worker/enqueue-periodic` backend calls FeedbackLens source polling and checks the weekly digest schedule.

## Cleanup and dedupe

- Empty feedback is rejected.
- Obvious spam such as repeated "buy now/click here/free money" plus suspicious URLs is rejected before storage.
- Text is normalized with Unicode folding, punctuation cleanup, whitespace collapse, stopword removal, and light stemming.
- Long feedback is compacted to 2000 characters by keeping the opening context plus sentences containing product-risk terms such as payment, checkout, export, crash, refund, and urgent.
- Near-duplicate matching uses token overlap plus sequence similarity.
- External source dedupe also checks `source` + `source_message_id`, so edited GitHub Issues or repeated polling do not create duplicate entries.
- `POST /feedback`, `POST /feedback/bulk`, and `POST /feedback/bulk-csv` skip near-duplicates.
- `GET /feedback/dedupe/summary` reports duplicate groups over the latest 500 entries.

## Local sentiment analysis

- VADER is the preferred local engine.
- Keyword scoring is the always-available fallback.
- Output is `sentiment`, `confidence`, `themes`, `is_urgent`, `draft_reply`, and `analysis_engine`.
- Theme focus terms from settings can bias local theme extraction.
- No provider key is required and no external generation request is made.

## Dashboard and digest

- `/feedback/summary/weekly` compares the latest seven days with the previous seven days.
- `/clusters` returns stable topic cluster ids based on local themes and normalized text.
- `/digest` returns urgent, high, and low cluster groups for manual digest generation.
- Weekly digest email reuses stored processed fields, sends only Monday at 9am in the user's configured `timezone`, and avoids sending twice on the same local date.
- Urgent feedback queues a `SystemOutbox` email immediately when `alert_email` is configured.
- The dashboard should present weekly trend, data quality, sentiment counts, urgent feedback, bulk import status, exports, and deterministic reply drafts.

## GitHub issue creation

- `/clusters/{id}/github-issue` creates one GitHub issue from a cluster.
- The issue body includes representative quotes, source names, authors, and links when present.
- Labels include `feedback-lens`, plus `bug` or `feature` when the cluster id and priority indicate it.

## CLI

- `feedbacklens login --api-key KEY`
- `feedbacklens sources add --type twitter --handle @myproduct`
- `feedbacklens feedback list --priority urgent`
- `feedbacklens clusters list --days 7`
- `feedbacklens clusters create-issue --id checkout --repo acme/app`

## Monetization and limits

- Free: 100 feedback items/month, 2 sources, manual + email only, 30-day history, no GitHub issue creation, no weekly digest.
- Pro: 5000 feedback items/month, 10 sources, manual/email/GitHub/Canny/Twitter/Reddit, GitHub issue creation, weekly digest, 180-day history.
- Team: 25000 feedback items/month, 50 sources, all Pro features, 365-day history.
- Twitter/X and Reddit are intentionally paid-plan only because those APIs can carry real provider cost and policy risk.

## Frontend implementation notes

- Use `/feedback/dedupe/summary` in the dashboard.
- Use `deduped` and `duplicate_of_id` to avoid rendering duplicates as new entries.
- Present the settings field `custom_prompt` as `Theme Focus`.
- Let users configure `timezone` with the weekly digest toggle.
- Show `spam_rejected` and `duplicates_skipped` after bulk/CSV imports.
- For email forwarding, send extracted text for text/CSV/JSON/log attachments in the `attachments[]` payload.
- Avoid copy that promises provider-based generation or external analysis.
