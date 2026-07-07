# FeedbackLens Frontend Contract

## Backend contract

- `GET /feedback` and `GET /feedback/list` return processed feedback entries with optional `priority` and `source` filters.
- `POST /feedback` creates one entry or returns an existing entry with `deduped: true` and `duplicate_of_id`.
- `POST /feedback/{id}/analyze` runs local sentiment analysis and returns `analysis_engine: "local_transformers"` or `"enhanced_keyword"`.
- `POST /feedback/{id}/draft-reply` returns a deterministic support reply draft.
- `POST /feedback/bulk` imports newline feedback through the full cleanup/dedupe/analysis pipeline and returns `created`, `ids`, `items`, `duplicates_skipped`, and `spam_rejected`.
- `POST /feedback/bulk-csv` imports CSV feedback from the `text` column through the full pipeline and returns `created`, `ids`, `items`, `duplicates_skipped`, `spam_rejected`, and `total_rows`.
- `GET /feedback/summary/weekly` returns the dashboard weekly summary and deltas.
- `GET /feedback/dedupe/summary` returns duplicate group counts and candidate ids.
- `GET /feedback/export?format=csv|xlsx|json` streams export files.
- `GET /settings/feedback-prefs` and `PUT /settings/feedback-prefs` manage local analysis focus terms, negative threshold, alert email, weekly digest preference, and `timezone`.
- `GET /sources` lists configured feedback sources.
- `POST /sources` configures `twitter`, `reddit`, `github`, `canny`, `email`, or `manual` sources.
- `DELETE /sources/{id}` disconnects a source, clears stored credentials/secrets, and keeps existing feedback history.
- `POST /feedback/ingest/email` receives parsed forwarded email feedback. Body supports `attachments[]` with `filename`, `content_type`, `text`, `content`, and `encoding`; text-like attachments are included in analysis.
- `POST /feedback/ingest/canny` receives Canny webhook feedback.
- `POST /feedback/ingest/github?source_id={id}` receives GitHub Issues webhooks and validates `x-hub-signature-256` when the source has a webhook secret.
- `GET /clusters?days=30` lists stable topic clusters ordered by priority.
- `GET /clusters/{id}` returns one cluster with sample quotes, source counts, sentiment counts, and priority.
- `POST /clusters/{id}/github-issue` creates a GitHub issue for a cluster when a GitHub source token and repo are configured.
- `GET /digest?days=7` returns manual digest data grouped into urgent, high, and low clusters.
- `POST /connect/github` starts the GitHub OAuth flow when the GitHub client id is configured.
- `GET /connect/github/callback?state=...&code=...` stores the GitHub OAuth token and marks the source connected.
- `POST /connect/twitter` starts Twitter/X OAuth with PKCE for Pro users.
- `GET /connect/twitter/callback?state=...&code=...` stores the Twitter/X token and marks the source connected.
- `POST /connect/reddit` starts Reddit OAuth for Pro users.
- `GET /connect/reddit/callback?state=...&code=...` stores the Reddit token and marks the source connected.
- `POST /feedback/cron/poll` is the cron endpoint for Twitter/X, Reddit, and GitHub issue polling.

## Frontend behavior

- Show duplicate responses as "matched existing feedback" instead of inserting a new row.
- Display `duplicates_skipped` after bulk imports.
- Display `/feedback/dedupe/summary` as a data-quality panel near the weekly insight panel.
- Display `/clusters` as the Urgent / High / Low board once the cluster UI is added.
- Use `/sources` to show source connection status and webhook/forward instructions.
- Label reply drafts and analysis as local or deterministic, not external generation.
- Keep `custom_prompt` as the API field for backward compatibility, but present it as "Theme Focus".

## Required states

- Empty state: prompt the user to paste feedback or import CSV.
- Loading state: skeleton rows plus metrics.
- Error state: retryable inline error if all summary/list calls fail.
- Duplicate state: success toast and refresh list without analyzing the duplicate.
- Bulk state: created count and duplicate skipped count.
- Source state: connected, needs auth, pending OAuth, or deleted.
- GitHub issue state: creating, created with issue URL, or missing repo/token.
- Urgent alert state: urgent items enqueue an email to `alert_email`; show alert configuration in settings.
- Polling state: connected sources show `last_polled_at` and `poll_frequency_hours`.
- Limit state: Free users can use manual/email with 100 feedback items/month and 2 sources; Pro users can use all sources, GitHub issues, weekly digest, 5000 feedback items/month, and 10 sources.
