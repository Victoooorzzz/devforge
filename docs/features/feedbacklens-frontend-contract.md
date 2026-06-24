# FeedbackLens Frontend Contract

## Backend contract

- `GET /feedback/list` returns processed feedback entries.
- `POST /feedback` creates one entry or returns an existing entry with `deduped: true` and `duplicate_of_id`.
- `POST /feedback/{id}/analyze` runs Local sentiment analysis and returns `analysis_engine: "vader"` or `"keyword"`.
- `POST /feedback/{id}/draft-reply` returns a deterministic support reply draft.
- `POST /feedback/bulk` imports newline feedback and returns `created`, `ids`, and `duplicates_skipped`.
- `POST /feedback/bulk-csv` imports CSV feedback from the `text` column and returns `created`, `ids`, `duplicates_skipped`, and `total_rows`.
- `GET /feedback/summary/weekly` returns the dashboard weekly summary and deltas.
- `GET /feedback/dedupe/summary` returns duplicate group counts and candidate ids.
- `GET /feedback/export?format=csv|xlsx|json` streams export files.
- `GET /settings/feedback-prefs` and `PUT /settings/feedback-prefs` manage local analysis focus terms, negative threshold, alert email, and weekly digest preference.
- `GET /sources` lists configured feedback sources.
- `POST /sources` configures `twitter`, `reddit`, `github`, `canny`, `email`, or `manual` sources.
- `POST /feedback/ingest/email` receives parsed forwarded email feedback.
- `POST /feedback/ingest/canny` receives Canny webhook feedback.
- `GET /clusters?days=30` lists stable topic clusters ordered by priority.
- `GET /clusters/{id}` returns one cluster with sample quotes, source counts, sentiment counts, and priority.
- `POST /clusters/{id}/github-issue` creates a GitHub issue for a cluster when a GitHub source token and repo are configured.
- `GET /digest?days=7` returns manual digest data grouped into urgent, high, and low clusters.
- `POST /connect/github` starts the GitHub OAuth flow when the GitHub client id is configured.

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
- Source state: connected, needs auth, or pending OAuth.
- GitHub issue state: creating, created with issue URL, or missing repo/token.
