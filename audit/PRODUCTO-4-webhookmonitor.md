# PRODUCTO 4 - WebhookMonitor

## Alcance auditado
- Frontend: `apps/webhookmonitor/frontend`
- Backend: `apps/webhookmonitor/backend/main.py`
- Compartido: outbox, security_utils, logic_bridge, worker.

## Bugs y vulnerabilidades
- El endpoint publico `/hook/{slug}` no exige firma por origen. Es esperado para captura, pero necesita rate limit robusto y visibilidad de abuso.
- Rate limit consulta la DB por minuto y endpoint. Funciona, pero puede ser costoso bajo abuso.
- Forwarding bloquea URLs privadas literales, pero hereda el gap DNS SSRF de `is_public_http_url`.
- Los headers capturados se exportan/listan completos; puede guardar secretos de webhooks de terceros.

## Arquitectura
- Buen patron de ingestion publica + persistencia async + outbox para forward.
- `detect_and_act_on_payment` mezcla un puente de producto cruzado dentro de ingestion; util pero aumenta acoplamiento.
- La configuracion y logs estan separados, pero falta un endpoint agregado de salud/reliability.

## Funcionalidad
- Valor actual: endpoint unico, logs, polling frontend, clear history, retry/forward, auto retry, silence alerts, cleanup, export.
- Falta valor: resumen de confiabilidad, redaccion/masking de headers sensibles, filtros avanzados, status de forward por request.

## Testing
- No hay tests dedicados para ingestion, rate limit, masking, retry o silence cron.
- Edge cases sin cubrir: payload binario, headers enormes, forward 5xx, retry con payload override no JSON, abuso de endpoint.

## Performance
- `list_logs` trae 100 requests con body completo; cuerpos grandes pueden hacer lenta la UI.
- Export limita 1000, razonable, pero incluye preview sin masking.
