# WebhookMonitor Replay and Search

## Backend contract

- `GET /webhooks/endpoints`: list endpoint configs with `id`, `uuid`, `name`, `endpoint_url`, `methods`, `created_at`, `is_active`.
- `POST /webhooks/endpoints`: create an endpoint. Body: `{ "name": string, "methods": ["POST"|"PUT"|"PATCH"|"DELETE"|"GET"] }`.
- `GET /webhooks/endpoints/{endpoint_id}/events`: list captured events for one endpoint.
- `GET /webhooks/events/{event_id}`: fetch one captured event.
- `POST /webhooks/events/{event_id}/replay`: replay an event.
  - Exact: `{ "mode": "exact" }`.
  - Modified: `{ "mode": "modified", "body_override": string, "headers_override": object }`.
  - Alternate URL: `{ "mode": "alternate", "target_url": "https://public.example/webhook", "body_override": string?, "headers_override": object? }`.
  - Response: `{ "status": "success"|"failed", "event": object, "target_url": string, "response_status": number|null, "error": string }`.
- `GET /webhooks/events/{event_id}/diff?base_request_id={event_id}`: same diff payload as `/webhooks/requests/{id}/diff`.
- `POST /webhooks/search`: search captured payloads. Body supports `json_path`, `equals`, `status`, `method`, `provider`, `date_from`, `date_to`, `limit`.

Replay target URLs must pass public HTTP(S) validation. Each replay is stored as a new `WebhookRequest` linked by `replay_of_request_id`.

## Frontend contract

- Event inspector must expose Replay exact, Replay modified, and Replay alternate.
- Alternate replay requires a Replay target URL input.
- Modified/alternate replay can edit body and headers JSON before sending.
- Search controls must expose JSON path, equals value, status, method filter, provider filter, Date from, and Date to.
- Search results replace the current event table and can be refreshed back through the normal logs call.
