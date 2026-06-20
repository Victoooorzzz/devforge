# WebhookMonitor CLI

## Backend contract

The CLI calls the same authenticated REST endpoints as the dashboard:

- `webhookmonitor endpoints create --name "Stripe Production"`
  - `POST /webhooks/endpoints`
- `webhookmonitor endpoints list`
  - `GET /webhooks/endpoints`
- `webhookmonitor events list --endpoint 1 --status failed`
  - `GET /webhooks/endpoints/{endpoint_id}/events?status=failed`
- `webhookmonitor events replay --id 123 --url https://example.com/webhook`
  - `POST /webhooks/events/{event_id}/replay`
- `webhookmonitor events diff --id 123 --with 122`
  - `GET /webhooks/events/{event_id}/diff?base_request_id={base_id}`
- `webhookmonitor events search --json-path type --equals payment_intent.succeeded`
  - `POST /webhooks/search`

The CLI reads `WEBHOOKMONITOR_API_KEY` and `WEBHOOKMONITOR_API_URL`, or a local config created with `webhookmonitor login --api-key KEY`.

## Frontend contract

Frontend does not consume the CLI directly, but dashboard labels and docs should match CLI terms: endpoints, events, replay, diff, search, status, provider, and JSON path.
