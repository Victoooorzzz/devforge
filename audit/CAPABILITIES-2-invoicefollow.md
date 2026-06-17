# CAPABILITIES 2 - InvoiceFollow

## PUEDE HACER
- Crear y listar facturas.
- Marcar facturas como pagadas.
- Pausar recordatorios por promesa de pago.
- Encolar recordatorios vencidos con tono escalado.
- Generar magic link de descarga y link publico de promesa.
- Calcular score de riesgo por cliente.
- Generar tono de cobranza con Gemini o fallback.
- Exportar facturas.

## NO PUEDE HACER
- Mostrar resumen ejecutivo de cashflow/riesgo sin leer toda la tabla.
- Configurar intervalos de recordatorio por usuario.
- Caducar/rotar promise tokens.
- Validar importes positivos y clientes completos de forma fuerte.

## LIMITACION RAIZ
- Diseno: muchas capacidades existen, pero faltan agregados de decision y politicas configurables.

## IMPACTO
- Alto: puede venderse como MVP, pero el valor de gestion mejora mucho con resumen financiero accionable.
