# DevForge Ecosistema v1.0

## Matriz de Productos, Planes de Cobro y Límites Técnicos

DevForge es una suite de micro-SaaS orientada a desarrolladores, freelancers, founders y equipos pequeños que necesitan automatizar tareas operativas: limpieza de datos, depuración de webhooks, análisis de feedback, seguimiento de precios y cobranza de facturas.

La suite se estructura en tres niveles comerciales:

| Plan     | Propósito                                    |
| -------- | -------------------------------------------- |
| **Free** | Prueba funcional con límites claros          |
| **Pro**  | Uso individual serio                         |
| **Team** | Uso en equipo, mayor escala y automatización |

Los límites de cada producto deben aplicarse en backend mediante feature flags, cuotas de uso, retención automática y validaciones por workspace.

---

# Reglas Globales del Ecosistema

## Planes

| Plan     | Descripción                                                           |
| -------- | --------------------------------------------------------------------- |
| **Free** | Acceso limitado para validar valor sin pago                           |
| **Pro**  | Plan individual con límites ampliados y automatización                |
| **Team** | Plan colaborativo con mayor capacidad, retención y features avanzadas |

## Sistemas Backend Requeridos

Cada producto debe respetar una capa común de control:

```txt
plans
features
usage_counters
quota_guard
billing_webhook
retention_jobs
audit_logs
upgrade_prompts
```

Funciones centrales recomendadas:

```python
can_use_feature(user, workspace, feature_name)
consume_quota(user, workspace, metric, amount=1)
get_plan_limits(workspace)
enforce_retention_policy(workspace)
```

## Reglas Técnicas Globales

| Regla                    | Descripción                                                                  |
| ------------------------ | ---------------------------------------------------------------------------- |
| Feature flags            | Cada herramienta debe validarse contra el plan activo                        |
| Cuotas diarias/mensuales | Todo uso sensible debe medirse                                               |
| Retención automática     | Los datos vencidos se eliminan según plan                                    |
| Rate limits              | Protección por usuario, IP y workspace                                       |
| Audit logs               | Registro de acciones relevantes                                              |
| Billing sync             | Polar/Stripe debe ser la fuente de verdad del plan                           |
| Upgrade prompts          | Cuando un usuario alcance un límite, mostrar motivo claro para subir de plan |

---

# 1. FileCleaner

## Descripción

**FileCleaner** es una herramienta de limpieza, validación y preparación de archivos para datos tabulares e imágenes. Permite procesar CSV, Excel, JSON e imágenes para dejarlos listos antes de importarlos a sistemas, CRMs, bases de datos o pipelines internos.

**Posicionamiento recomendado:**

> Convierte archivos desordenados en datos listos para producción.

## Herramientas y Librerías del Backend

| Área                       | Herramientas                                                        |
| -------------------------- | ------------------------------------------------------------------- |
| Procesamiento y carga      | `pandas`, `openpyxl`, módulo nativo `csv`                           |
| Detección automática       | `csv.Sniffer` para delimitador y cabecera                           |
| Limpieza básica            | `pandas` para nulos, duplicados exactos y espacios                  |
| Normalización estructurada | `re`, `pandas`                                                      |
| Fechas                     | Conversión a ISO8601 UTC                                            |
| Teléfonos                  | Normalización a E.164                                               |
| Países                     | Normalización a códigos ISO                                         |
| Montos y monedas           | Extracción mediante regex de símbolos y códigos                     |
| Fuzzy matching             | `RapidFuzz` o `thefuzz`                                             |
| Algoritmos fuzzy           | Levenshtein Ratio, Partial Ratio, Token Sort Ratio, Token Set Ratio |
| Jaro-Winkler               | Opcional mediante `RapidFuzz` o `jellyfish`                         |
| Validación de esquemas     | Motor personalizado en Python                                       |
| Anomalías                  | IQR, Z-score, MAD                                                   |
| Multimedia y EXIF          | `Pillow` / PIL                                                      |

## Funciones Principales

| Función                | Descripción                                                   |
| ---------------------- | ------------------------------------------------------------- |
| Limpieza básica        | Elimina filas vacías, duplicados exactos y espacios sobrantes |
| Normalización          | Estandariza fechas, teléfonos, países, monedas y montos       |
| Duplicados difusos     | Detecta registros similares con errores humanos               |
| Validación de esquemas | Valida emails, rangos, enums, regex, nulos y claves cruzadas  |
| Anomalías              | Detecta outliers numéricos y formatos inconsistentes          |
| EXIF/privacy           | Remueve metadatos sensibles de imágenes                       |
| Exportación            | CSV, XLSX y JSON                                              |
| Reporte de limpieza    | Resume todos los cambios aplicados                            |

## Límites por Plan

| Característica             |                Free |                                  Pro |               Team |
| -------------------------- | ------------------: | -----------------------------------: | -----------------: |
| Tamaño máximo de archivo   |               10 MB |                               100 MB |             500 MB |
| Limpieza básica            |                  Sí |                                   Sí |                 Sí |
| Normalización              | Máx. 1 regla activa |                     Reglas ampliadas |   Reglas ampliadas |
| Detección de anomalías     |                  No |                                   Sí |                 Sí |
| Duplicados difusos         |                  No |                    Hasta 1,000 filas | Hasta 10,000 filas |
| Validación de esquemas     |                  No |           Hasta 5 reglas por archivo |   Reglas ampliadas |
| Limpieza EXIF / privacidad |          Hasta 5 MB |                          Hasta 50 MB |       Hasta 150 MB |
| Retención en S3/R2         |            24 horas |                             48 horas |             7 días |
| Procesamiento por lotes    |                  No | Hasta 10 archivos en cola secuencial |     Batch paralelo |
| Reporte de limpieza        |              Básico |                             Completo |           Completo |
| Exportación CSV/XLSX/JSON  |                  Sí |                                   Sí |                 Sí |

## Límites Internos Recomendados

| Límite             |        Free |          Pro |         Team |
| ------------------ | ----------: | -----------: | -----------: |
| Archivos por día   |           5 |          100 |        1,000 |
| Máximo de columnas |          50 |          200 |          500 |
| Preview máximo     | 1,000 filas | 10,000 filas | 50,000 filas |
| Timeout por job    |         30s |         120s |         300s |

---

# 2. Webhook Monitor

## Descripción

**Webhook Monitor** es una herramienta para recibir, inspeccionar, buscar, comparar, reenviar y depurar webhooks. Está pensada para desarrolladores que integran Stripe, GitHub, Shopify, PayPal, Canny u otros servicios con eventos HTTP.

**Posicionamiento recomendado:**

> Mira exactamente qué webhook falló, por qué falló y reprodúcelo en segundos.

## Herramientas y Librerías del Backend

| Área                 | Herramientas                                       |
| -------------------- | -------------------------------------------------- |
| API e ingesta        | `FastAPI`                                          |
| Endpoints dinámicos  | Rutas generadas por workspace/proyecto             |
| Validación de firmas | `hmac`, `hashlib`, `cryptography`                  |
| Cifrado              | `cryptography.fernet`                              |
| Reenvío HTTP         | `httpx` asíncrono                                  |
| Reglas condicionales | `jsonpath_ng`                                      |
| Diff de payloads     | Algoritmo recursivo personalizado en Python        |
| Replay               | Cola persistente en base de datos / `SystemOutbox` |
| Exportación          | cURL y Postman Collections                         |

## Funciones Principales

| Función                | Descripción                                      |
| ---------------------- | ------------------------------------------------ |
| Endpoint único         | URL dedicada para recibir eventos                |
| Historial de eventos   | Logs con headers, body, status y timestamp       |
| Payload encryption     | Cifrado de payloads sensibles                    |
| Signature validation   | Verificación de Stripe, GitHub, Shopify, etc.    |
| Replay manual          | Reenvío de eventos a servidores externos/locales |
| Retries automáticos    | Reintentos programados en Team                   |
| Diffing                | Comparación entre payloads                       |
| Log search             | Búsqueda avanzada dentro de payloads             |
| Conditional forwarding | Reglas para reenviar según contenido JSON        |
| Export dev tools       | cURL y Postman                                   |

## Límites por Plan

| Característica            |      Free |            Pro |                         Team |
| ------------------------- | --------: | -------------: | ---------------------------: |
| Endpoints activos         |         1 |             10 |                           50 |
| Eventos por día           |       100 |         10,000 |                       50,000 |
| Retención de logs         |    7 días |        30 días |                      90 días |
| Payload máximo por evento |    256 KB |           1 MB |                         5 MB |
| Cifrado de payloads       |        Sí |             Sí |                           Sí |
| Validación de firmas      |        No |             Sí |                           Sí |
| Reglas de forwarding      |        No | Hasta 3 reglas |             Reglas ampliadas |
| Replay                    |        No |         Manual | Manual + retries automáticos |
| Diffing                   |        No |             Sí |                           Sí |
| Búsqueda avanzada         |        No |             Sí |                           Sí |
| Exportación               | Solo cURL | cURL + Postman |               cURL + Postman |

## Límites Internos Recomendados

| Límite                      | Free | Pro |  Team |
| --------------------------- | ---: | --: | ----: |
| Requests por minuto         |   20 | 300 | 1,500 |
| Replays por día             |   No | 500 | 5,000 |
| Reglas activas por endpoint |   No |   3 |    20 |
| Timeout forwarding          |   No | 10s |   30s |

---

# 3. FeedbackLens

## Descripción

**FeedbackLens** centraliza, analiza y clasifica opiniones de clientes desde múltiples fuentes. Ayuda a detectar temas repetidos, sentimiento, urgencia, spam, duplicados y oportunidades de producto.

**Posicionamiento recomendado:**

> Convierte feedback disperso en prioridades accionables.

## Herramientas y Librerías del Backend

| Área                    | Herramientas                                    |
| ----------------------- | ----------------------------------------------- |
| Ingesta multi-fuente    | Webhooks HTTP y conectores OAuth2               |
| Fuentes externas        | GitHub, Canny, X/Twitter, Reddit, email, manual |
| Análisis de sentimiento | VADER mediante `nltk` o modelo custom           |
| NLP temático            | Extracción interna de tags y palabras clave     |
| Deduplicación semántica | Stemming + similitud Jaccard                    |
| Spam detection          | Reglas heurísticas y scoring interno            |
| GitHub Issues           | `httpx` contra GitHub REST API                  |
| Reportes                | Plantillas HTML + `email_service`               |
| Adjuntos                | Procesamiento básico de PDF/imágenes            |

## Funciones Principales

| Función          | Descripción                                |
| ---------------- | ------------------------------------------ |
| Ingesta manual   | Registro directo de feedback               |
| Ingesta email    | Captura de opiniones desde correo          |
| Fuentes externas | GitHub, Canny, Reddit, X/Twitter           |
| Sentimiento      | Clasificación positiva, neutral o negativa |
| Spam detection   | Filtrado de ruido                          |
| Tags automáticos | Temas frecuentes y palabras clave          |
| Deduplicación    | Agrupación de feedback similar             |
| GitHub Issues    | Creación automática de issues              |
| Digest semanal   | Reporte de tendencias por email            |
| Adjuntos         | Lectura básica de PDFs e imágenes          |

## Límites por Plan

| Característica            |           Free |         Pro |         Team |
| ------------------------- | -------------: | ----------: | -----------: |
| Feedback procesado al mes |      100 items | 5,000 items | 25,000 items |
| Fuentes activas           |              2 |          10 |           50 |
| Canales permitidos        | Manual + Email |       Todos |        Todos |
| Retención del historial   |        30 días |    180 días |     365 días |
| Análisis de sentimiento   |             Sí |          Sí |           Sí |
| Detección de spam         |             Sí |          Sí |           Sí |
| Desduplicación semántica  |             No |          Sí |           Sí |
| Digest semanal            |             No |       Email |        Email |
| GitHub Issues automáticos |             No |          Sí |           Sí |
| Procesamiento de adjuntos |             No |          Sí |           Sí |

## Nota Comercial

El precio Pro puede lanzarse como beta a bajo costo, pero este producto tiene potencial para subir a un precio superior porque combina integraciones, análisis NLP, automatización y valor directo para equipos de producto.

## Límites Internos Recomendados

| Límite                     | Free |       Pro |                  Team |
| -------------------------- | ---: | --------: | --------------------: |
| Tamaño máximo por feedback | 5 KB |     50 KB |                100 KB |
| Adjuntos por mes           |   No |       500 |                 5,000 |
| Issues creados por mes     |   No |       500 |                 5,000 |
| Digests por workspace      |   No | 1 semanal | 1 semanal + variantes |

---

# 4. PriceTrackr

## Descripción

**PriceTrackr** monitorea precios de productos en páginas web, guarda historial, genera gráficos de tendencia y envía alertas cuando detecta cambios relevantes.

**Posicionamiento recomendado:**

> Monitorea precios automáticamente y recibe alertas cuando algo cambia.

## Herramientas y Librerías del Backend

| Área                  | Herramientas                              |
| --------------------- | ----------------------------------------- |
| Scraping              | `httpx`, `BeautifulSoup`                  |
| Extracción de precios | Regex con `re`                            |
| Monedas soportadas    | USD, EUR, GBP, PEN/S/. y símbolos comunes |
| User-Agents           | Rotación aleatoria                        |
| Control de scraping   | Sleep adaptativo y rate limiting          |
| Gráficos              | Motor interno SVG                         |
| Alertas               | `email_service` y webhooks vía `httpx`    |
| Scheduler             | Cola persistente en base de datos         |
| Historial             | Series temporales por tracker             |

## Funciones Principales

| Función             | Descripción                               |
| ------------------- | ----------------------------------------- |
| Trackers de URL     | Monitoreo de páginas de producto          |
| Price extraction    | Detección de moneda y monto               |
| Historial           | Registro de fluctuaciones                 |
| Gráficos SVG        | Tendencia visual de precios               |
| Alertas email       | Notificación ante cambios                 |
| Alertas webhook     | Integración con sistemas externos         |
| Custom selectors    | Selectores definidos por usuario          |
| Rotación User-Agent | Menor bloqueo de scraping                 |
| Pausa por errores   | Suspensión temporal si una tienda bloquea |

## Límites por Plan

| Característica       |        Free |                   Pro |                  Team |
| -------------------- | ----------: | --------------------: | --------------------: |
| Trackers activos     |      5 URLs |              100 URLs |              500 URLs |
| Frecuencia mínima    |    Cada 24h |               Cada 1h |            Cada 10min |
| Historial de precios |     30 días |              180 días |              365 días |
| Alertas por email    | Con retraso |          Instantáneas |          Instantáneas |
| Alertas por webhook  |          No |                    Sí |                    Sí |
| Gráficos SVG         |          Sí |                    Sí |                    Sí |
| User-Agent rotation  |      Básica |              Avanzada |              Avanzada |
| Proxy rotation       | No / básica |              Avanzada |               Premium |
| Custom selectors     |          No |                    Sí |                    Sí |
| Tiendas soportadas   |    Estándar | Estándar + selectores | Estándar + selectores |

## Límites Internos Recomendados

| Límite                               |     Free |   Pro |       Team |
| ------------------------------------ | -------: | ----: | ---------: |
| Timeout por request                  |       5s |   10s |        15s |
| Máximo HTML descargado               |     1 MB |  3 MB |       5 MB |
| Errores consecutivos antes de pausa  |        3 |     5 |         10 |
| Chequeos diarios aproximados máximos |        5 | 2,400 |     72,000 |
| Rate limit por dominio               | Estricto | Medio | Adaptativo |

## Nota Técnica

El scraping debe manejarse con cuidado porque puede generar costos, bloqueos y fallos por cambios en HTML. PriceTrackr debe tener pausas automáticas, límite por dominio, detección de errores repetidos y selector fallback.

---

# 5. InvoiceFollow

## Descripción

**InvoiceFollow** automatiza el seguimiento de facturas pendientes mediante recordatorios por email, análisis de respuestas, conciliación con pasarelas de pago y reportes financieros.

**Posicionamiento recomendado:**

> Cobra facturas atrasadas automáticamente sin perseguir clientes manualmente.

## Herramientas y Librerías del Backend

| Área               | Herramientas                                                      |
| ------------------ | ----------------------------------------------------------------- |
| Modelado de datos  | `sqlmodel`                                                        |
| Validación         | `pydantic`                                                        |
| Importación masiva | `pandas`, `openpyxl`                                              |
| Email parsing      | Algoritmos Python para nombres, fechas y montos                   |
| NLP de respuestas  | Clasificador heurístico por intención                             |
| Intenciones        | Prórroga, disputa, confirmación de pago, rechazo, promesa de pago |
| Conciliación       | Webhooks de Stripe y PayPal                                       |
| Gmail sync         | OAuth2 con Gmail API                                              |
| Reportes           | Digest semanal vía email                                          |
| API access         | Endpoints para automatización externa                             |

## Funciones Principales

| Función                | Descripción                            |
| ---------------------- | -------------------------------------- |
| Crear facturas         | Registro manual o importación masiva   |
| Seguimiento automático | Emails de recordatorio                 |
| NLP de respuestas      | Clasifica intención del cliente        |
| Stripe/PayPal          | Detecta pagos mediante webhooks        |
| Gmail sync             | Monitorea buzón de facturación         |
| Digest semanal         | Reporte financiero agregado            |
| API access             | Automatización vía endpoints           |
| Historial              | Registro de recordatorios y respuestas |
| Equipo                 | Colaboradores en Team                  |

## Límites por Plan

| Característica          |          Free |                            Pro |        Team |
| ----------------------- | ------------: | -----------------------------: | ----------: |
| Facturas activas        |             5 |                             50 |         200 |
| Emails de cobranza      |      25 / mes |                      500 / mes | 2,000 / mes |
| NLP de respuestas       |      10 / mes |                      200 / mes | 1,000 / mes |
| Usuarios del workspace  |             1 |                              1 |           5 |
| Conexiones de pago      |            No |                        Hasta 2 |    Hasta 10 |
| Stripe                  |            No |                             Sí |          Sí |
| PayPal                  |            No | Limitado / según configuración |          Sí |
| Retención del historial |       30 días |                        90 días |    365 días |
| Gmail sync              |            No |                             Sí |          Sí |
| Digest semanal          |            No |                             Sí |          Sí |
| Acceso API              |            No |                             Sí |          Sí |
| Importación masiva      | No / limitada |                             Sí |          Sí |

## Límites Internos Recomendados

| Límite                            |       Free |          Pro |          Team |
| --------------------------------- | ---------: | -----------: | ------------: |
| Emails por día                    |         10 |          100 |           500 |
| Máximo adjunto importación        |       5 MB |        25 MB |        100 MB |
| Frecuencia mínima de recordatorio |     7 días |       3 días |  Configurable |
| Dominios de envío                 | Compartido |   Verificado |    Verificado |
| Webhooks de pago                  |         No | 2 conexiones | 10 conexiones |

## Nota Legal y Operativa

InvoiceFollow debe evitar comportamiento agresivo o spam. Se recomienda:

* límites de frecuencia por cliente;
* historial de emails enviados;
* plantillas editables;
* dominio verificado;
* opción de pausar recordatorios;
* registro de conciliación;
* tono profesional en mensajes de cobranza.

---

# Matriz General de Precios

## Precio Beta v1

| Producto        | Free |           Pro |   Team |
| --------------- | ---: | ------------: | -----: |
| FileCleaner     |   $0 |      $9.99/mo | $49/mo |
| Webhook Monitor |   $0 |      $9.99/mo | $49/mo |
| FeedbackLens    |   $0 | $9.99/mo beta | $49/mo |
| PriceTrackr     |   $0 |      $9.99/mo | $49/mo |
| InvoiceFollow   |   $0 | $9.99/mo beta | $49/mo |

## Precio Recomendado Futuro

| Producto        | Pro futuro recomendado | Team futuro recomendado |
| --------------- | ---------------------: | ----------------------: |
| FileCleaner     |               $9.99/mo |                  $49/mo |
| Webhook Monitor |                 $15/mo |                  $49/mo |
| FeedbackLens    |                 $19/mo |                  $79/mo |
| PriceTrackr     |        $19/mo o $29/mo |                  $79/mo |
| InvoiceFollow   |                 $19/mo |         $49/mo o $79/mo |

---

# Bundle Recomendado

Además de vender productos separados, DevForge puede venderse como suite.

## DevForge Founder Toolkit

| Plan   |  Precio | Incluye                                |
| ------ | ------: | -------------------------------------- |
| Solo   |  $29/mo | Acceso Pro a 2 productos               |
| Growth |  $59/mo | Acceso Pro a los 5 productos           |
| Team   | $129/mo | Acceso Team limitado a los 5 productos |

Este bundle permite que un usuario entre por una herramienta y descubra el resto del ecosistema.

---

# Prioridad de Lanzamiento

| Prioridad | Producto        | Motivo                                        |
| --------- | --------------- | --------------------------------------------- |
| 1         | Webhook Monitor | Dolor claro para devs, demo rápida            |
| 2         | FileCleaner     | Utilidad inmediata y fácil de probar          |
| 3         | InvoiceFollow   | Dolor económico directo                       |
| 4         | FeedbackLens    | Alto valor, pero más integraciones            |
| 5         | PriceTrackr     | Buen producto, pero mayor riesgo por scraping |

---

# Checklist Final Antes de Lanzar

## Producto

* Cada producto tiene una landing clara.
* Cada Free permite probar valor real.
* Cada Pro resuelve un caso de uso serio.
* Cada Team ofrece escala o colaboración.
* Cada límite está explicado sin lenguaje técnico innecesario.

## Backend

* Límites aplicados en servidor.
* Plan sincronizado desde Polar/Stripe.
* Feature flags por producto.
* Cuotas diarias/mensuales.
* Retención automática.
* Rate limits por IP, usuario y workspace.
* Logs de auditoría.
* Jobs de limpieza.
* Manejo de errores por integraciones externas.

## Billing

* Webhook de suscripción activa.
* Downgrade seguro.
* Bloqueo por falta de pago.
* Upgrade inmediato.
* Página de billing por workspace.
* Facturas o recibos disponibles.

## UX

* Onboarding menor a 3 minutos.
* Demo rápida por producto.
* Mensajes claros al alcanzar límites.
* Botón de upgrade contextual.
* Dashboard de uso.
* Historial de acciones.

---

# Conclusión

DevForge v1.0 queda compuesto por cinco micro-SaaS:

1. **FileCleaner** — limpia y valida datos.
2. **Webhook Monitor** — depura webhooks.
3. **FeedbackLens** — convierte feedback en acciones.
4. **PriceTrackr** — monitorea precios y alerta cambios.
5. **InvoiceFollow** — automatiza cobranza de facturas.

El alcance v1 debe congelarse aquí.

La prioridad ya no es agregar más features, sino:

```txt
implementar límites reales,
cerrar pricing,
pulir onboarding,
activar pagos,
medir uso,
lanzar.
```

DevForge no necesita una sexta herramienta todavía.
Necesita salir al mundo, recibir golpes reales y aprender del mercado.
