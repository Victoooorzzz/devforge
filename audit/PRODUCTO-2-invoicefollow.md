# PRODUCTO 2 - InvoiceFollow

## Alcance auditado
- Frontend: `apps/invoicefollow/frontend`
- Backend: `apps/invoicefollow/backend/main.py`
- Compartido: auth, email, outbox, worker, payments.

## Bugs y vulnerabilidades
- `_build_email_body` genera un `magic_token` pero el token no queda asociado al usuario en `InvoiceMagicLink`; si alguien obtiene el token, accede al JSON de la factura hasta que expire.
- `public_promise` usa `promise_token` permanente por factura y no expira. Es util, pero deberia tener caducidad o rotacion.
- El API base del link de email usa `NEXT_PUBLIC_API_URL` desde el backend, un nombre de variable frontend; deberia ser un env backend explicito o `FRONTEND_URL`/API public URL documentado.
- Amount acepta cualquier float sin validacion de positivo.

## Arquitectura
- El core de recordatorios, score de clientes, magic links, AI tone y export vive en un `main.py` unico.
- `SystemOutbox` separa el envio de emails del cron, buen patron para deploy serverless/Render.
- La logica de scoring esta inline y no es reutilizable ni testeable sin DB.

## Funcionalidad
- Valor actual: creacion/listado de facturas, marcar pagado, pausar recordatorios, cron con tono escalado, magic link de descarga, promesa publica de pago, client risk scores, AI tone y export.
- Falta valor: resumen financiero accionable (overdue total, promised, cash at risk), filtros/orden por riesgo, vencimientos proximos, configuracion de calendario/intervalos por usuario.

## Testing
- No hay tests dedicados para invoices, scoring, magic links o cron.
- Edge cases sin cubrir: importes negativos, emails vacios, due date futura, token usado/expirado, promesa repetida, factura sin client_email.

## Performance
- `client_scores` carga todas las facturas del usuario y agrupa en memoria; aceptable al inicio, pero podria paginarse o agregarse en SQL.
- El cron consulta todas las facturas vencidas pendientes; falta limite/batching por ciclo.
