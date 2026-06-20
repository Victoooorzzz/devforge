# WebhookMonitor Plan Limits and Retention

## Backend contract

- Free/trial:
  - 1 endpoint.
  - 100 events per day.
  - 7 day retention.
  - Replay, diff, and search are monetization hooks for upgrade prompts.
- Paid/Pro:
  - 10 endpoints.
  - 10,000 events per day.
  - 30 day retention.
  - Replay, diff, and search enabled.
- Team target:
  - 50 endpoints.
  - 100,000 events per day.
  - 90 day retention.
  - Multiple users.

Ingestion enforces the daily event limit per user before reading the payload body. Endpoint creation enforces the endpoint count limit. Cleanup cron deletes captured events outside each user's retention window.

## Frontend contract

- Endpoint creation UX must show remaining endpoint allowance for the current plan.
- Event throttle errors should display the backend `detail` message and direct the user to upgrade.
- Replay/search/diff controls should remain visible but can be upgrade-gated once plan capability is exposed to the frontend.
