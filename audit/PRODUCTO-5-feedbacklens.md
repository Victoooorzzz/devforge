# PRODUCTO 5 - FeedbackLens

## Alcance auditado
- Frontend: `apps/feedbacklens/frontend`
- Backend: `apps/feedbacklens/backend/main.py`
- Compartido: auth, email, outbox, worker.

## Bugs y vulnerabilidades
- El producto depende de Gemini, pero tiene fallback VADER/keywords, lo cual evita bloqueo por API key.
- El bulk import JSON limita 500 items; CSV limita 5MB y 500 rows procesadas, bien. Falta devolver cuantas filas fueron omitidas por limite.
- Custom prompt se inserta directo en prompt de Gemini; aceptable como preferencia del usuario, pero puede inducir salidas invalidas y deberia tener limite de longitud.
- HTML de digest incluye texto con mojibake por encoding, problema de polish/legibilidad.

## Arquitectura
- Todo el dominio vive en `main.py`: modelos, settings, AI, resumen, cron, import/export y draft reply.
- La forma `FeedbackAnalysis` es clara; el fallback hace el producto usable sin red.
- Weekly summary existe en backend, pero el dashboard principal no lo aprovecha como panel de decision.

## Funcionalidad
- Valor actual: feedback manual, bulk text, CSV import, analysis AI/fallback, urgent flag, draft reply, weekly summary, digest email y export.
- Falta valor: panel de insight visible, trend del periodo anterior, acciones por urgencia, integraciones de entrada (Slack/Zendesk), deduplicacion.

## Testing
- No hay tests dedicados para sentiment fallback, bulk limits, summary ni draft reply.
- Edge cases sin cubrir: texto vacio, prompt gigante, CSV sin columna, themes_json corrupto, Gemini JSON invalido.

## Performance
- `list_feedback` limita 100, correcto para UI inicial.
- Export trae todos los feedbacks del usuario; necesita paginacion si crece.
- Weekly summary carga todas las entradas de la semana por usuario; aceptable al inicio.
