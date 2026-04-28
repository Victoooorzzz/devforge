# DevForge Ecosystem - Hoja de Ruta y Tareas Pendientes (Roadmap)

## Estado Actual del Proyecto (Abril 2026)

**✅ Infraestructura y Backend**
- **Monorepo:** Configurado correctamente con Turborepo, compartiendo paquetes (`@devforge/ui` y `@devforge/core`).
- **Despliegues:** Frontends desplegados en Vercel y Backends desplegados en Render.
- **Lógica Core:** La base de datos, APIs, CRON jobs, web scraping e IA (Gemini) están implementados.

**✅ Frontend (Conexión API)**
- Las 5 aplicaciones ya tienen sus páginas de `login`, `register` y `dashboard` programadas.
- Todas están configuradas usando `apiClient` para comunicarse con sus respectivos backends (hacen POST, GET de listas, suben archivos, etc.).

---

## ❌ ¿Por qué te sale error 404 en la página de Settings?

Mencionaste que al entrar a `Settings` te sale un 404. El motivo es porque **la página de Settings y su endpoint en el backend NO existen en ninguna de las 5 apps.**

Actualmente las carpetas de Next.js en las 5 aplicaciones solo tienen:
- `/login`
- `/register`
- `/dashboard`

Y los backends en Python solo tienen endpoints relacionados con su función principal (ej. `/invoices`, `/trackers`, `/webhooks`), pero **no hay un endpoint general de configuración (`/settings`)** para gestionar la cuenta, perfil, suscripciones o variables específicas de la app.

---

## 📋 Tareas Pendientes (Lo que REALMENTE falta por programar)

Para que el ecosistema esté 100% completo, debes implementar lo siguiente en cada aplicación (tanto en Frontend como en Backend):

### 1. Configurar Producción en Vercel (Crítico)
- **Frontend:** Configurar en Vercel la variable de entorno `NEXT_PUBLIC_API_URL` apuntando a las URLs de producción de Render (ej. `https://devforge-backend.onrender.com`). Si no lo haces, tus frontends intentarán conectarse a `http://localhost:8000` en producción y fallarán.

### 2. Implementar la Página y API de "Settings" (Global)
- **Frontend:** Crear la carpeta y página `src/app/dashboard/settings/page.tsx` en las 5 aplicaciones (el enlace que te daba 404).
- **Backend:** Crear un nuevo router `settings_router` en `backend_core` o en el `main.py` de cada app para permitir al usuario actualizar su perfil, ver si tiene plan activo y cambiar preferencias.

---

### Tareas Faltantes Específicas por SaaS:

#### 📄 InvoiceFollow (Recordatorios de Facturas)
- **Frontend:** Falta crear un botón en la tabla para marcar una factura como pagada (ya tienes el endpoint listo en el backend `/invoices/{id}/mark-paid`, pero olvidaste agregar el botón visual en `page.tsx`).
- **Backend/Frontend (Settings):** Falta poder configurar desde qué correo se envían los recordatorios o personalizar la plantilla del correo de cobranza.

#### 📉 PriceTrackr (Rastreador de Precios)
- **Frontend:** Falta crear un botón en el dashboard para poder borrar (Delete) un producto de la lista (el endpoint `/trackers/{id}` ya existe en el backend, pero no hay botón para borrarlo en la interfaz).
- **Backend/Frontend (Settings):** Falta configurar notificaciones (ej. a qué correo enviar la alerta cuando el precio baje al objetivo deseado).

#### 🪝 WebhookMonitor (Capturador de Webhooks)
- **Frontend:** La lista de webhooks se carga una sola vez al entrar. Faltaría implementar "polling" (un `setInterval` o websockets) para que los nuevos webhooks aparezcan en tiempo real sin recargar la página. 
- **Backend:** Falta programar un endpoint para eliminar todo el historial de webhooks (`DELETE /webhooks/requests`) y agregar un botón de "Limpiar" en el frontend.

#### 🧹 FileCleaner (Clasificador/Limpiador de Archivos)
- **Backend:** El endpoint actual `/files/upload` sube el archivo, verifica que pese menos de 50MB, y devuelve un link simulado `/files/download/...`. **Falta la lógica real** que abra el archivo (CSV/PDF), lo limpie o procese y genere un link de descarga válido.
- **Frontend:** Falta el botón real para borrar archivos subidos o cancelar descargas.

#### 🧠 FeedbackLens (Analizador de Feedback)
- **Frontend:** El dashboard principal parece estar completo.
- **Backend/Frontend (Settings):** En la nueva página de Settings faltaría permitir que el usuario ponga instrucciones de IA personalizadas (Custom Prompts) para Gemini, o configurar alertas automáticas cuando se reciba un feedback "muy negativo".
