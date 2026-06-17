# Cross-Product Analysis

## Dependencias compartidas
- `packages/backend_core/main_factory.py` crea FastAPI, CORS, health, auth, Polar y worker.
- `packages/backend_core/universal_main.py` importa todos los productos y arma el backend unico de Render.
- `packages/backend_core/product_access.py` protege features por trial o acceso Polar por producto.
- `packages/core/lib/api.ts` centraliza llamadas JSON, pero uploads/exports aun usan `fetch` manual en dashboards.
- `packages/ui` comparte layout/dashboard shell y componentes landing.

## Codigo duplicado
- Los 5 dashboards reimplementan export/download con `fetch` manual y token de `localStorage`.
- Settings pages repiten profile/subscription management.
- Cada producto guarda agregados de negocio inline en `main.py`.
- Cron endpoints repiten validacion `CRON_SECRET`, mientras el backend universal ya tiene `verify_cron_secret`.

## Inconsistencias API
- API base: `apiClient` usa fallback `http://localhost:8000`; fetch manual usa `NEXT_PUBLIC_API_URL || ""`.
- Settings de FileCleaner define router sin endpoints, mientras otros productos si tienen preferencias.
- Nombres de env mezclan frontend/backend (`NEXT_PUBLIC_API_URL` usado para links generados en backend de InvoiceFollow).
- Landing de FileCleaner no coincide con backend real de data cleaning.

## Riesgos compartidos
- SSRF: `is_public_http_url` bloquea IPs literales privadas, pero no resuelve DNS.
- Typecheck: `turbo run typecheck` solo ejecuta paquetes con script; los frontends de productos no tienen `typecheck`.
- Tests: solo hay 17 tests Python, enfocados en helpers; no hay tests de dominio por producto.
- Los `.tsbuildinfo` estaban trackeados previamente y ahora aparecen borrados; `.gitignore` ya incluye `*.tsbuildinfo` en cambios no commiteados previos.

## Modulos compartibles recomendados
- `packages/core/lib/api.ts`: agregar helpers para upload y download/export.
- `packages/backend_core/product_insights.py`: helpers puros para summaries por producto, testeables sin DB.
- `packages/backend_core/cron_auth.py` o uso unico de `verify_cron_secret`.
- `packages/backend_core/sensitive_data.py`: masking de headers/body en WebhookMonitor.
- `packages/backend_core/data_quality.py`: limpieza tabular reusable para FileCleaner.
