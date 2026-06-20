# WebhookMonitor Event Export

## Goal

Allow a user to export one owned webhook event as an executable cURL command or a Postman Collection v2.1 file from the dashboard inspector.

## API Contract

### GET /webhooks/requests/{request_id}/export?format=curl

Returns `text/plain` with a shell-ready cURL command.

Response headers:

```http
Content-Disposition: attachment; filename=webhook-request-{request_id}.curl.sh
Content-Type: text/plain
```

Command contents:

```bash
curl --request POST 'https://webhookmonitor.devforgeapp.pro/hook/{slug}' \
  --header 'content-type: application/json' \
  --header 'stripe-signature: t=1,v1=sig' \
  --data-raw '{"type":"invoice.paid"}'
```

The export preserves replay-relevant headers such as provider signature headers and content type. It omits transport-generated headers that cURL must recalculate: `host`, `content-length`, `transfer-encoding`, and `connection`.

### GET /webhooks/requests/{request_id}/export?format=postman

Returns `application/json` with a Postman Collection v2.1 document.

Response headers:

```http
Content-Disposition: attachment; filename=webhook-request-{request_id}.postman_collection.json
Content-Type: application/json
```

Collection requirements:

- `info.schema` is `https://schema.getpostman.com/json/collection/v2.1.0/collection.json`.
- One collection item is generated per exported event.
- The item preserves HTTP method, URL, exportable headers, and raw body.
- Raw body language is `json` when the body parses as JSON, otherwise `text`.

## Authorization And Safety

- The endpoint uses the authenticated user from `get_current_user`.
- The request must belong to the authenticated user's WebhookMonitor endpoint.
- Unknown or foreign `request_id` values return `404`.
- The export intentionally uses the captured raw body because the feature is for debugging and replay. UI copy should make clear that exported files can contain secrets from the original webhook.

## Frontend Contract

The WebhookMonitor dashboard inspector exposes two event-level actions after selecting a delivery:

- `Export cURL`
- `Export Postman`

Both actions use the shared `downloadFile` helper with:

- `/webhooks/requests/${selected.id}/export?format=curl`
- `/webhooks/requests/${selected.id}/export?format=postman`

Successful downloads show a success toast. Failed downloads show a retryable error toast.

## Tests

- `tests/test_webhook_monitor_moat.py` verifies cURL and Postman output for an owned request.
- `tests/test_webhook_dashboard_moat_ux.py` verifies dashboard controls and this contract document.
