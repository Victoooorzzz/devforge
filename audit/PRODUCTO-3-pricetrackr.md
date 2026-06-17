# PRODUCTO 3 - PriceTrackr

## Alcance auditado
- Frontend: `apps/pricetrackr/frontend`
- Backend: `apps/pricetrackr/backend/main.py`
- Compartido: scraper, security_utils, price_alerts, worker.

## Bugs y vulnerabilidades
- `is_public_http_url` bloquea IPs privadas literales, pero no resuelve DNS; un dominio publico podria resolver a IP privada y causar SSRF durante scraping/forwarding.
- `create_tracker` ejecuta scraping sin timeout local propio; depende de `scraper.fetch_price`.
- `alert_threshold` permite valores negativos o incoherentes.
- Si `new_price` es `None`, `last_checked` puede no actualizarse aunque si hubo intento real.

## Arquitectura
- Buen aislamiento relativo: scraping y alert rules viven en `backend_core`.
- El flujo cron -> outbox -> handler evita scraping sincrono masivo.
- El resumen de oportunidad/ahorro no existe como dominio compartido; el dashboard arma experiencia desde listas crudas.

## Funcionalidad
- Valor actual: tracking de URL, historial de precios, frecuencia configurable, threshold alert, test alert, stock alert, export.
- Falta valor: ranking de oportunidades, ahorro potencial, health del scraper por tracker, limites por plan, pausa/reactivacion.

## Testing
- Cobertura existente para price extraction, URL publica y alerts.
- No hay tests de endpoints, frecuencia, threshold invalidos, historial o errores de scraper.

## Performance
- `run_price_updates` puede encolar todos los trackers due sin limite.
- `process_price_check` hace price y stock en dos fetches potenciales al mismo URL.
- Historial limita 30 puntos, bien para UI inicial.
