# FeedbackLens Production Pipeline

## Scope

FeedbackLens turns raw feedback into a triage dashboard without external generation services. The core path is collection, cleanup, Local sentiment analysis, theme extraction, near-duplicate detection, weekly summary, export, and reply drafting.

## Collection

- Manual textarea creates one feedback item.
- Bulk textarea imports one item per line.
- CSV upload imports up to 500 rows from the `text` column.
- `/sources` stores source configuration for Twitter/X, Reddit, GitHub Issues, Canny, email forwarding, and manual entry.
- `/feedback/ingest/email` receives parsed forwarded email feedback.
- `/feedback/ingest/canny` receives Canny webhook feedback.
- GitHub OAuth starts at `/connect/github`; issue creation uses the configured GitHub source token and repo.

## Cleanup and dedupe

- Empty feedback is rejected.
- Text is normalized with Unicode folding, punctuation cleanup, whitespace collapse, stopword removal, and light stemming.
- Near-duplicate matching uses token overlap plus sequence similarity.
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
- Weekly digest email reuses stored processed fields and does not block on missing entries.
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

## Frontend implementation notes

- Use `/feedback/dedupe/summary` in the dashboard.
- Use `deduped` and `duplicate_of_id` to avoid rendering duplicates as new entries.
- Present the settings field `custom_prompt` as `Theme Focus`.
- Avoid copy that promises provider-based generation or external analysis.
