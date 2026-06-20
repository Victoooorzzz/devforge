# WebhookMonitor Signatures and Forwarding

## Backend contract

- `GET /settings/webhook-prefs` returns forwarding, retry, alert, and signature config:
  - `forward_url`, `fallback_url`
  - `retry_max_attempts`, `retry_backoff_seconds`, `forward_timeout_seconds`
  - `alert_email`, `slack_webhook_url`, `discord_webhook_url`
  - `signature_provider`, `signature_secret_set`
- `PUT /settings/webhook-prefs` accepts the same fields plus `signature_secret`.
- Signature providers:
  - Stripe: `Stripe-Signature`, HMAC-SHA256 with timestamp tolerance.
  - GitHub: `X-Hub-Signature-256`.
  - Shopify: `X-Shopify-Hmac-Sha256`.
  - Generic: `X-Signature` with HMAC-SHA256, HMAC-SHA1, or RSA-SHA256.
- Captured events persist `signature_valid`, `signature_error`, `signature_provider`, `forward_error`, `last_retry_status`, `query_params`, and `ip_address`.
- Forwarding retries use configured attempts/backoff. Fallback URL is used after attempts are exhausted.
- Email, Slack, and Discord alerts fire on signature failures and final forward failures when configured.

All forward, fallback, Slack, Discord, and replay URLs must be public HTTP(S) URLs to avoid SSRF.

## Frontend contract

- Settings must expose Forward URL, Fallback URL, Retry Attempts, Backoff Seconds, Forward Timeout, Alert Email, Slack Webhook URL, Discord Webhook URL, Signature Provider, and Signature Secret.
- The dashboard inspector must show signature provider, valid/invalid/not checked state, signature error, source IP, event id, forward status, and forward error.
