# Roadmap Progress

## Baseline
- Branch: `main`.
- Worktree pre-existente: cambios sin commit en Polar/config/package lock y artefactos `tsconfig.tsbuildinfo`.
- Python baseline: `python -m unittest discover -s tests` -> 17 tests OK.
- Typecheck baseline: `pnpm run typecheck` -> OK, pero solo 3 paquetes ejecutados.
- Lint baseline: `pnpm run lint` -> OK con warnings existentes.

## Iteracion 1 - Quick Wins
- Estado: completada.
- Cambios:
  - Agregado `typecheck` a los 5 frontends de producto.
  - Centralizados API URL, uploads y downloads en `packages/core/lib/api.ts`.
  - Migrados exports/uploads de dashboards a helpers compartidos.
  - Sacados del tracking los `tsconfig.tsbuildinfo`; quedan cubiertos por `*.tsbuildinfo`.
- Verificacion:
  - `rg "NEXT_PUBLIC_API_URL \|\| \"\"" apps/*/frontend/src/app/dashboard/page.tsx` -> sin matches en dashboards.
  - `pnpm run typecheck` -> 8 tasks OK: core, ui, template y 5 frontends.
  - `python -m unittest discover -s tests` -> 17 tests OK.
  - `pnpm run lint` -> 9 tasks OK, warnings existentes de imagen/hooks.
- Commit: `iter-1: quick-wins-stability`.

## Iteracion 2 - Deuda Tecnica
- Estado: completada.
- Cambios:
  - Agregado `tests/test_product_insights.py` con 5 casos de summaries por producto.
  - Implementado `packages/backend_core/product_insights.py` con helpers puros sin DB/FastAPI.
  - Ajustada la formula de `cash_at_risk` para no descontar promesas futuras de deuda vencida.
- Verificacion:
  - RED: `python -m unittest tests.test_product_insights -v` -> fallo esperado por `ModuleNotFoundError: product_insights`.
  - GREEN focalizado: `python -m unittest tests.test_product_insights -v` -> 5 tests OK.
  - Suite: `python -m unittest discover -s tests` -> 22 tests OK.
- Commit: `iter-2: shared-product-insights`.

## Iteracion 3 - VALUE FEATURES
- Estado: completada.
- Cambios:
  - FileCleaner: endpoint `/files/summary` y cards de processed/rows saved/quality actions/errors.
  - InvoiceFollow: endpoint `/invoices/summary`, cash-at-risk visible y bloque de promesas de pago.
  - PriceTrackr: endpoint `/trackers/summary` y cards de drops, stock y savings.
  - WebhookMonitor: endpoint `/webhooks/summary` y cards de volumen 24h, retries y failed forwards.
  - FeedbackLens: consumo de `/feedback/summary/weekly` en dashboard.
  - Incluido fix de producto ya presente en workspace para usar `settings.s3_bucket_name` en cleanup/delete de FileCleaner.
- Verificacion:
  - `python -m unittest discover -s tests` -> 22 tests OK.
  - `pnpm run typecheck` -> 8 tasks OK.
  - `pnpm run lint` -> 9 tasks OK, warnings existentes.
  - `python -c "import sys; sys.path.insert(0, 'packages'); import backend_core.universal_main; print('universal_main import ok')"` -> OK.
  - `rg '/(files|invoices|trackers|webhooks)/summary|summary/weekly' apps packages -n` -> endpoints/consumos encontrados.
- Commit: `iter-3: value-feature-insight-panels`.

## Iteracion 4 - Optimizacion
- Estado: completada.
- Cambios:
  - Agregado `packages/backend_core/sensitive_data.py` para masking de headers/campos sensibles.
  - Agregado `packages/backend_core/data_limits.py` para limites compartidos.
  - WebhookMonitor ahora redacted headers en list y agrega `headers_preview`/body preview seguro en export.
  - FileCleaner corta `fuzzy-check` con 413 sobre 5000 filas para evitar O(n2) excesivo.
- Verificacion:
  - RED: `python -m unittest tests.test_security_helpers -v` -> fallo esperado por `ModuleNotFoundError: data_limits`.
  - GREEN focalizado: `python -m unittest tests.test_security_helpers -v` -> 3 tests OK.
  - Suite: `python -m unittest discover -s tests` -> 25 tests OK.
  - `python -c "import sys; sys.path.insert(0, 'packages'); import backend_core.universal_main; print('universal_main import ok')"` -> OK.
  - `pnpm run typecheck` -> 8 tasks OK.
  - `pnpm run lint` -> 9 tasks OK, warnings existentes.
- Commit: `iter-4: optimize-security-and-performance`.

## Iteracion 5 - Polish
- Estado: pendiente.
