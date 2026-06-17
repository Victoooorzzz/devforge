# DevForge 5-Product Execution Roadmap

## Estado base verificado
- Rama de trabajo: `main` (por instruccion del usuario, sin worktree).
- Productos auditados: FileCleaner, InvoiceFollow, PriceTrackr, WebhookMonitor, FeedbackLens.
- Tests Python base: `python -m unittest discover -s tests` -> 17 tests OK.
- Typecheck base: `pnpm run typecheck` -> OK, pero solo 3 paquetes ejecutados porque los frontends no declaran `typecheck`.
- Lint base: `pnpm run lint` -> OK con warnings existentes de `<img>` y hooks.
- Arbol sucio previo: Polar/config, `.gitignore`, package lock, `tsconfig.tsbuildinfo` borrados y `.eslintrc.json` sin trackear. No se revierten.

## Iteracion 1 - Quick Wins: estabilidad base

**Objetivo:** hacer que verificacion frontend cubra realmente los 5 productos y reducir bugs de API base en exports/uploads.

| Tarea | Archivos | MoSCoW | Esfuerzo |
|---|---|---:|---:|
| Agregar `typecheck` a los 5 frontend package.json | `apps/*/frontend/package.json` | Must | S |
| Crear helper compartido para API base, upload y download blob | `packages/core/lib/api.ts`, `packages/core/index.ts` | Must | M |
| Migrar dashboards que usan fetch manual a helpers compartidos | `apps/*/frontend/src/app/dashboard/page.tsx` | Should | M |
| Registrar resultado | `ROADMAP-PROGRESS.md` | Must | S |

**Criterios de exito**
- `pnpm run typecheck` ejecuta core, ui y los 5 frontends.
- `python -m unittest discover -s tests` sigue OK.
- No hay uso de `NEXT_PUBLIC_API_URL || ""` en dashboards.
- Commit: `iter-1: quick-wins-stability`

## Iteracion 2 - Deuda Tecnica: insights compartidos testeables

**Objetivo:** extraer logica de summaries de producto a helpers puros para que Value Features no aumenten acoplamiento.

| Tarea | Archivos | MoSCoW | Esfuerzo |
|---|---|---:|---:|
| Agregar tests RED para summaries por producto | `tests/test_product_insights.py` | Must | M |
| Implementar helpers puros de summaries | `packages/backend_core/product_insights.py` | Must | M |
| Exportar/usar helpers sin tocar endpoints aun | `packages/backend_core/__init__.py` si aplica | Could | S |
| Registrar resultado | `ROADMAP-PROGRESS.md` | Must | S |

**Criterios de exito**
- Los tests nuevos fallan antes de implementar helpers.
- `python -m unittest discover -s tests` OK despues.
- Commit: `iter-2: shared-product-insights`

## Iteracion 3 - VALUE FEATURES: paneles de decision por producto

**Objetivo central:** exponer valor agregado visible en cada producto sin romper contratos existentes.

| Producto | Feature | Archivos | MoSCoW | Esfuerzo |
|---|---|---|---:|---:|
| FileCleaner | `/files/summary` con files procesados, filas ahorradas y errores | `apps/filecleaner/backend/main.py`, dashboard | Must | M |
| InvoiceFollow | `/invoices/summary` con overdue amount, promised amount y cash at risk | `apps/invoicefollow/backend/main.py`, dashboard | Must | M |
| PriceTrackr | `/trackers/summary` con drops, stock changes y oportunidad | `apps/pricetrackr/backend/main.py`, dashboard | Must | M |
| WebhookMonitor | `/webhooks/summary` con volumen, retry pressure y silencio | `apps/webhookmonitor/backend/main.py`, dashboard | Must | M |
| FeedbackLens | usar `/feedback/summary/weekly` en dashboard principal | `apps/feedbacklens/frontend/src/app/dashboard/page.tsx` | Must | S |
| Tests | ampliar helpers si hacen falta | `tests/test_product_insights.py` | Must | S |
| Progreso | registrar resultados | `ROADMAP-PROGRESS.md` | Must | S |

**Criterios de exito**
- Cada dashboard muestra al menos un bloque de insight accionable.
- Todos los endpoints nuevos exigen auth/acceso por su router existente.
- `python -m unittest discover -s tests`, `pnpm run typecheck` y `pnpm run lint` pasan.
- Commit: `iter-3: value-feature-insight-panels`

## Iteracion 4 - Optimizacion: seguridad y performance pragmatica

**Objetivo:** reducir riesgos evidentes sin introducir infraestructura pesada.

| Tarea | Archivos | MoSCoW | Esfuerzo |
|---|---|---:|---:|
| Agregar helper de masking para headers sensibles de webhooks | `packages/backend_core/sensitive_data.py`, tests | Must | M |
| Aplicar masking en list/export de WebhookMonitor | `apps/webhookmonitor/backend/main.py` | Must | M |
| Limitar fuzzy-check por cantidad de filas ademas de MB | `apps/filecleaner/backend/main.py`, tests | Should | S |
| Registrar resultado | `ROADMAP-PROGRESS.md` | Must | S |

**Criterios de exito**
- Headers como authorization, cookie y x-signature no se exponen completos en logs/list/export.
- Fuzzy check rechaza datasets demasiado grandes para O(n2).
- Tests y typecheck/lint OK.
- Commit: `iter-4: optimize-security-and-performance`

## Iteracion 5 - Polish: documentacion operativa y reporte

**Objetivo:** dejar el repo mantenible y el estado final claro.

| Tarea | Archivos | MoSCoW | Esfuerzo |
|---|---|---:|---:|
| Actualizar docs de produccion con checks y envs reales | `PRODUCTION_SETUP.md` | Should | S |
| Completar reporte final de auditoria/ejecucion | `FINAL-REPORT.md` | Must | M |
| Cerrar progreso al 100% | `ROADMAP-PROGRESS.md` | Must | S |
| Registrar blockers si quedo alguno | `BLOCKERS.md` si aplica | Could | S |

**Criterios de exito**
- `FINAL-REPORT.md` resume cambios por producto, metricas, deuda residual y siguientes pasos.
- Verificacion final fresca ejecutada y registrada.
- Commit: `iter-5: polish-docs-final-report`
