# PRODUCTO 1 - FileCleaner

## Alcance auditado
- Frontend: `apps/filecleaner/frontend`
- Backend: `apps/filecleaner/backend/main.py`
- Compartido: `packages/backend_core`, `packages/core`, `packages/ui`

## Bugs y vulnerabilidades
- El producto promete metadata stripping, compresion y conversion, pero el backend real procesa CSV/XLSX. Hay gap comercial-funcional entre landing y producto.
- Uploads y AI analyze dependen de `fetch` manual con `NEXT_PUBLIC_API_URL || ""`, distinto del `apiClient`; esto puede romper produccion si falta la variable o si cambia el manejo de auth.
- `settings_router` existe sin endpoints y sin proteccion explicita; hoy no aporta valor y puede confundir el contrato de API.
- La limpieza de S3/R2 borra errores silenciosamente; tolerable para cleanup, pero no deja metrica por archivo no eliminado.
- Riesgo SSRF general mitigado en `security_utils` para URLs de otros productos; FileCleaner no expone URL remota directa, por lo que su riesgo principal es storage/config.

## Arquitectura
- Valor de dominio concentrado en un solo `main.py` grande. La limpieza de dataframe, upload, jobs, demo, export y AI viven juntos.
- La cola `SystemOutbox` es una buena base para procesamiento async, pero los handlers estan acoplados al modelo y al storage.
- El backend universal importa modelos/routers de este producto para registrar tablas. Esto facilita deploy unico, pero acopla startup a imports de todas las apps.

## Funcionalidad
- Valor actual: upload CSV/XLSX, limpieza basica, magic-clean, fuzzy duplicates, AI suggestions, demo publico, export de metadata y descarga por URL prefirmada.
- Falta/rompe valor: landing desalineada, no hay vista agregada de calidad/ahorro, no hay dry-run de limpieza antes de subir a R2, no hay limites de filas para fuzzy O(n2).

## Testing
- No hay tests dedicados para la limpieza de FileCleaner ni para jobs.
- Cobertura indirecta solo por tests compartidos (`security_utils`, price extraction, Polar).
- Edge cases sin cubrir: CSV vacio, columnas mixtas, Excel corrupto, storage no configurado, archivos grandes, fuzzy con miles de filas.

## Performance
- `fuzzy-check` compara todas las filas contra todas las filas: O(n2), limitado por 20MB pero aun riesgoso.
- `magic-clean` parsea fechas dos veces por columna y ejecuta carga completa en memoria.
- Upload usa R2 correctamente por stream en el endpoint principal, pero `magic-clean` lee todo el archivo antes de subir.
