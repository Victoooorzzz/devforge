# 🚀 Guía de Despliegue: DevForge Monorepo (6 Dominios)

Esta guía te permite desplegar toda la infraestructura en menos de 30 minutos usando el flujo de **Vercel + Railway**.

---

## 1. Preparación de Código
1. Crea un repositorio privado en GitHub.
2. Sube todo el contenido de la carpeta `devforge`:
   ```bash
   git init
   git add .
   git commit -m "Initial micro-saas empire"
   git remote add origin <tu-repo-url>
   git push -u origin main
   ```

---

## 2. Despliegue de Frontends (Vercel)
Deberás crear **6 proyectos** en Vercel (uno para cada dominio). Para cada uno:

1. Selecciona tu repositorio de GitHub.
2. En **Project Settings**:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: `apps/<nombre-del-app>/frontend` (Ej: `apps/filecleaner/frontend`)
3. En **Environment Variables**:
   - Copia las variables de tu `.env` local (Stripe keys, API URLs, etc.).
4. En **Domains**:
   - Añade tu dominio oficial (ej: `filecleaner.io`) y sigue las instrucciones para configurar el DNS.

---

## 3. Despliegue de Backends (Railway)
Deberás crear **6 servicios** (o uno con múltiples routers) en Railway:

1. Selecciona "New Project" -> "GitHub Repo".
2. Railway detectará automáticamente el `Procfile` que creé en cada carpeta de backend.
3. En cada servicio, configura las **Environment Variables**:
   - `DATABASE_URL`: Tu URL de PostgreSQL (puedes crear una base de datos PostgreSQL ahí mismo en Railway).
   - `STRIPE_WEBHOOK_SECRET`: El secreto que te da Stripe al configurar el webhook.
4. Railway te dará una URL (ej: `api-filecleaner.railway.app`). Copia esta URL y ponla como `NEXT_PUBLIC_API_URL` en el frontend de Vercel correspondiente.

---

## 4. Configuración de Stripe
Para cada producto:
1. Ve al Dashboard de Stripe -> Developers -> Webhooks.
2. Añade un endpoint: `https://tu-api-en-railway.app/stripe/webhook`.
3. Selecciona los eventos: `checkout.session.completed`, `customer.subscription.deleted`.

---

## ✅ Resumen de Puertos y Dominios
| Producto | Carpeta Root (Vercel) | Backend Port (Railway) |
|---|---|---|
| Main Site | `apps/devforge-site/frontend` | (N/A) |
| File Cleaner | `apps/filecleaner/frontend` | 8001 |
| Invoice Follow | `apps/invoicefollow/frontend` | 8002 |
| Price Tracker | `apps/pricetrackr/frontend` | 8003 |
| Webhook Monitor | `apps/webhookmonitor/frontend` | 8004 |
| Feedback Lens | `apps/feedbacklens/frontend` | 8005 |
