# CAPABILITIES 4 - WebhookMonitor

## PUEDE HACER
- Crear endpoint unico por usuario.
- Ingerir webhooks publicos con limite de body y rate limit por minuto.
- Listar logs con polling.
- Borrar historial.
- Reenviar webhooks via outbox.
- Forward automatico con retries.
- Detectar silencio y limpiar logs antiguos.
- Exportar logs.

## NO PUEDE HACER
- Maskear secretos de headers/body antes de persistir/listar.
- Mostrar resumen de confiabilidad y fallos.
- Filtrar por status de forward o error.
- Defender SSRF por DNS rebinding/resolucion privada.

## LIMITACION RAIZ
- Diseno: excelente utilidad tecnica inicial, pero faltan controles de seguridad/observabilidad para equipos reales.

## IMPACTO
- Critico/alto: el valor es fuerte, pero logs de secretos y forward URLs requieren hardening antes de escalar.
