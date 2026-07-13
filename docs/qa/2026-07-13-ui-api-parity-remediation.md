# Paridad UI/API y remediación de QA — 2026-07-13

## Resultado

La paridad de los flujos centrales de los cinco productos queda cubierta en código y protegida por `tests/test_ui_api_parity_contract.py`. Los endpoints sin UI que permanecen son superficies deliberadamente técnicas: ingestión pública, cron/workers, health/metrics operativas, OAuth callbacks y CLI/automation.

| Producto | Ciclo de vida visible | Operaciones centrales UI ↔ API | Estado |
| --- | --- | --- | --- |
| WebhookMonitor | crear y eliminar endpoints; borrar historial | listar/capturar, búsqueda avanzada, retry, replay, diff, schema y exportaciones | Cubierto |
| FileCleaner | subir, cancelar y eliminar archivos | análisis, limpieza, Deep Clean, quality review, estado, descarga y exportación | Cubierto |
| PriceTrackr | crear y eliminar trackers | frecuencia real de 10 min, umbral, confirmación, historial, test de alerta y exportación directa | Cubierto |
| FeedbackLens | crear y eliminar feedback y fuentes | análisis/reanálisis, borradores, dedupe, clusters, digest, importación y exportación | Cubierto |
| InvoiceFollow | crear, editar y eliminar registros | detectar/confirmar borrador, importar, pause/resume, paid, timeline y exportación | Cubierto |

## Cierres por producto

### WebhookMonitor

- `Clear History` usa el contrato obligatorio `confirm=CONFIRM` y normaliza errores FastAPI antes de renderizarlos.
- La búsqueda del servidor ya no es sobrescrita por el polling cada cinco segundos y ofrece `Clear search`.
- El replay exacto al propio capture URL no persiste una segunda copia manual.
- El borrado de endpoint elimina el endpoint y su historial/idempotencia, liberando cuota.

### FileCleaner

- Deep Clean deduplica de nuevo después de normalizar y reporta invalidaciones de email, fecha e importe.
- El análisis local detecta duplicados, whitespace y valores inválidos obvios.
- XLSX conserva el nombre de la primera hoja y fuzzy matching evita agrupar identidades incompatibles.
- Dashboard refleja `needs_review`, muestra el reporte y completa el borrado con confirmación visible.

### PriceTrackr

- Frecuencia Team de 10 minutos está alineada en modelo, validación, migración, worker y selector UI.
- El umbral se edita como estado controlado y se persiste por API sin cerrar el panel.
- Los contadores excluyen soft-deletes y la exportación descarga CSV/XLSX/JSON directamente.

### FeedbackLens

- Existe borrado de feedback con ownership y control de dos pasos en UI.
- Fuentes con estado `deleted` dejan de listarse; la UI permite crear y eliminar fuentes.
- Crear, importar, eliminar o reanalizar refresca resumen, dedupe, clusters y digest.
- El análisis síncrono y el worker comparten el mismo pipeline local completo.

### InvoiceFollow

- El detector ya no envía `source=forward` sin `message_id`; esa validación 422 era la causa del borrador invisible.
- El dashboard permite editar por `PUT` y eliminar por `DELETE`, con limpieza de logs, replies, pagos y auditoría asociados.
- Los campos `Issue date` y `Due date` tienen etiquetas accesibles.
- El landing actual no promete pagos parciales, disputas ni aprobación manual. Esas funciones no se presentan como disponibles y no se añadieron como estados especulativos.

## APIs deliberadamente sin UI

- Endpoints públicos de captura/forwarding e ingestión de proveedores.
- Cron, cleanup, polling, enqueue/process y callbacks OAuth/webhook.
- Health, delivery-status detallado, analytics operativas y comandos CLI.
- Aliases legacy conservados por compatibilidad.

Estas exclusiones no son gaps de producto: no son acciones interactivas de dashboard y mantienen controles de autenticación, firma o secreto propios.

## Gate de producción

- Commit funcional: `825c049` en `main`.
- Vercel: los cinco proyectos frontend quedaron `READY` sobre `825c049`.
- Render: `devforge-universal-backend` quedó `live` sobre `825c049`; `/health` respondió HTTP 200.
- Dominios canónicos: los cinco dashboards `*.devforgeapp.pro` respondieron HTTP 200.
- OpenAPI vivo: confirmó `DELETE /feedback/{entry_id}`, `DELETE /invoices/{invoice_id}`, `GET /trackers/export-file`, `POST /webhooks/search` y `POST /files/deep-clean`.
- QA autenticada: WebhookMonitor mantuvo resultados y mostró `Clear search`; PriceTrackr conservó el primer carácter del umbral; FeedbackLens abrió creación/gestión de fuentes; InvoiceFollow detectó un borrador con 100% de confianza, lo confirmó y eliminó el registro QA sin dejar residuo.

El gate funcional y de paridad queda cerrado. La rotación del token de Vercel expuesto por la salida del CLI se registra como acción operativa separada; el script quedó endurecido en `377b260` para redactar tokens en futuras ejecuciones.
