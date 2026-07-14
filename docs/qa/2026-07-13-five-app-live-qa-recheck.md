# DevForge: recheck de QA en producción de las 5 apps

**Fecha:** 2026-07-13  
**Entorno:** `*.devforgeapp.pro` y backend unificado de Render  
**Alcance:** repetición de los hallazgos anteriores después de los fixes, con pruebas de UI, API autenticada, workers, archivos descargados, tests y builds.

## Veredicto ejecutivo

| App | Resultado del recheck | Estado |
| --- | --- | --- |
| FileCleaner | Deep Clean, AI Analyze y fuzzy matching entregan el resultado corregido en producción | Aprobado |
| WebhookMonitor | Captura, búsqueda vacía y validación de replay corregidas; backend de limpieza confirmado | Aprobado con límite de automatización en el segundo clic visual |
| PriceTrackr | Conteos, frecuencia Team de 10 minutos y elegibilidad del worker corregidos | Aprobado |
| FeedbackLens | Crear/analizar actualiza conteo, digest y clusters; eliminación backend limpia el registro | Aprobado |
| InvoiceFollow | Pago parcial, disputa, aprobación manual, edición y eliminación están disponibles | Aprobado |

No se reprodujeron nuevamente los bloqueantes originales. OAuth de Google/Gmail y Stripe/PayPal permanecen fuera del alcance por depender de aprobaciones externas.

## FileCleaner

- Fixture viva: `John   Doe`, duplicado equivalente, teléfono peruano sin prefijo, importe inválido, fecha inválida y correo inválido.
- `POST /files/ai-analyze`: HTTP 200 y 3 sugerencias de valores de negocio inválidos.
- `POST /files/fuzzy-check?threshold=85`: HTTP 200, 1 grupo y 2 filas afectadas; no agrupó la fila distinta.
- `POST /files/deep-clean`: HTTP 200, 3 filas reducidas a 2, nombre `John Doe`, teléfono `+51987654321`, fecha y correo inválidos convertidos a nulos.
- El fix adicional requerido en producción fue compatibilidad con los dtypes de texto de pandas 3.
- UI: límite Team de 500 MB y texto “up to your plan limit” confirmados.

## WebhookMonitor

- Se creó un endpoint QA, se recibió un webhook real y el historial mostró la entrega.
- Búsqueda avanzada con consulta vacía: devolvió 1 entrega y no produjo HTTP 422.
- Replay editado con `{`: mensaje `Payload must be valid JSON before retrying` y botón deshabilitado.
- Primer clic de limpieza: cambia a `Confirm clear` y muestra advertencia explícita.
- `DELETE /webhooks/requests?confirm=CONFIRM`: HTTP 200; lectura posterior de logs: 0.
- Se corrigieron carreras entre el borrado, el polling y respuestas iniciadas antes de limpiar mediante confirmación síncrona, estado optimista y generación de refresco.
- Limitación del instrumento: el navegador semántico enfocó, pero no despachó de forma fiable el segundo clic sobre el botón ya activo. Por ello el segundo clic visual no se declara comprobado de extremo a extremo; sí están confirmados el estado armado, el contrato backend, los tests, el typecheck, el build y el despliegue productivo.
- Limpieza QA: endpoint temporal eliminado y logs en 0.

## PriceTrackr

- Dashboard productivo: `Watched Links = 2` y `Items total = 2`; los soft-deletes ya no inflan los contadores.
- Paso 2 de creación: opción `Every 10 Minutes (Team)` visible.
- Los dos trackers existentes muestran la opción `10m Interval` en edición.
- El scheduler incluye trackers `active` y `needs_selector`; el procesador actualiza `last_checked` cuando el scrape termina sin cambio de precio.
- La salud dejó de marcar ambos trackers como stale; Anthouse se recuperó y Drinkflyers quedó clasificado `out_of_stock`.
- `GET /trackers/list`: solo 2 trackers activos, ambos sin `deleted_at`; sus sitios continúan requiriendo selector/soporte anti-bot, que es una condición de scraping externa y no un leak de worker.
- No se creó un tracker duplicado durante el recheck.

## FeedbackLens

- Se creó un feedback QA negativo y urgente desde el dashboard.
- Sin recargar, el conteo cambió de 4 a 5.
- Weekly insight cambió a 1 feedback, 1 negativo y 1 urgente; digest cambió a 1 cluster activo y la cola de temas añadió `Checkout`.
- `GET /feedbacklens/digest?days=7`: HTTP 200 con claves `days`, `generated_at`, `summary`, `urgent`, `high` y `low`.
- `DELETE /feedback/{id}`: HTTP 200; tras refrescar, el dashboard volvió a 4, el registro QA desapareció y el weekly insight volvió a cero.
- La UI mostró el estado `Confirm delete`; el segundo clic semántico tuvo la misma limitación de despacho del instrumento observada en WebhookMonitor, por lo que la eliminación final se ejecutó mediante el endpoint nativo autenticado.

## InvoiceFollow

- Se creó la factura QA `QA-PARTIAL-20260713` por USD 1,000 y apareció con acciones `Paid`, `Partial`, `Dispute`, `Pause` y `Delete`.
- Pago parcial USD 250: HTTP 200; UI mostró `Paid $250.00`, `Awaiting manual approval` y acción `Approve`.
- Secuencia backend: `approve` 200, `dispute` 200 y `approve` 200.
- UI final: conservó `Paid $250.00`, retiró la aprobación pendiente y volvió a `Invoice Original`.
- `GET /digest?days=7`: HTTP 200 y devolvió el digest financiero de InvoiceFollow, sin colisión con FeedbackLens.
- La factura QA fue eliminada: HTTP 200.

## Backend, workers y rutas compartidas

- `/health`: 200.
- `/worker/enqueue-periodic`: 200.
- `/worker/process`: 200.
- `/worker/cleanup`: 200.
- `/feedbacklens/digest`: digest de feedback.
- `/digest`: digest financiero de InvoiceFollow.
- El OpenAPI productivo incluye `/invoices/{invoice_id}/partial-payment` y `/feedbacklens/digest`.

## Cambios desplegados

- `8bb81d3`: fixes funcionales de las cinco apps.
- `7911547`: compatibilidad FileCleaner con pandas 3.
- `0000bdb` a `fe7c51c`: endurecimiento iterativo de limpieza/refresco en WebhookMonitor durante el recheck vivo.
- Frontends productivos desplegados en Vercel y backend desplegado en Render.

## Riesgos / pendientes no bloqueantes

- Rotar `VERCEL_TOKEN`: el CLI lo incluyó accidentalmente en una sugerencia mostrada en el log de ejecución durante el primer despliegue. No se reproduce el valor en este informe.
- Repetir manualmente una vez el segundo clic visual de `Confirm clear` y `Confirm delete` en un navegador normal, porque el controlador semántico usado en QA no despachó de forma fiable acciones sucesivas sobre el mismo botón activo.
- PriceTrackr sigue dependiendo de compatibilidad por tienda, selectores y medidas anti-bot; los dos trackers actuales no están stale, pero ambos conservan `needs_selector` como diagnóstico.
- No se probaron OAuth Google/Gmail ni conciliación Stripe/PayPal.

## Gate final

Los bloqueantes funcionales originales quedaron corregidos y desplegados. La suite puede continuar hacia producción controlada, manteniendo como checklist manual los dos segundos clics y rotando el token de Vercel antes del lanzamiento.
