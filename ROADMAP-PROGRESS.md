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
- Estado: pendiente.

## Iteracion 4 - Optimizacion
- Estado: pendiente.

## Iteracion 5 - Polish
- Estado: pendiente.
