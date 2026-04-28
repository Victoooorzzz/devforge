# 🚀 Guía de Despliegue: DevForge Monorepo (6 Dominios)

Esta guía te permite desplegar toda la infraestructura usando **Vercel + Railway**.

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

### ⚡ Deploy rápido con script (recomendado)

Desde la raíz del monorepo:

```powershell
# Deploy todas las apps
.\scripts\deploy-all.ps1

# Deploy una app específica
.\scripts\deploy-all.ps1 -AppName filecleaner
```

El script:
1. Buildea con Turbo desde la raíz (resolviendo `@devforge/ui` y `@devforge/core`)
2. Deploya los archivos estáticos (`out/`) de cada app a su proyecto Vercel

### 🔧 Setup inicial de Vercel (una sola vez)

Vincular cada proyecto desde su carpeta `frontend/`:

```powershell
cd apps/filecleaner/frontend && vercel link --project file-cleaner --yes
cd apps/invoicefollow/frontend && vercel link --project invoice-follow --yes
cd apps/pricetrackr/frontend && vercel link --project price-trackr --yes
cd apps/webhookmonitor/frontend && vercel link --project webhook-monitor --yes
cd apps/feedbacklens/frontend && vercel link --project feedback-lens --yes
cd apps/devforge-site/frontend && vercel link --project devforge-empire --yes
```

### ⚠️ IMPORTANTE: Monorepo

Todas las apps dependen de `@devforge/ui` y `@devforge/core` via `workspace:*`.
**NO deployar desde subcarpetas individuales** — siempre buildear desde la raíz con Turbo:

```bash
pnpm build --filter=filecleaner   # Resuelve workspace deps correctamente
```

El `devforge-site` (landing page principal) también puede deployarse desde la raíz del monorepo
usando el `vercel.json` raíz que ya está configurado:

```powershell
vercel link --project devforge-empire --yes
vercel --prod --yes
```

---

## 3. Despliegue de Backends (Railway)
Deberás crear **6 servicios** (o uno con múltiples routers) en Railway:

1. Selecciona "New Project" -> "GitHub Repo".
2. Railway detectará automáticamente el `Procfile` que creé en cada carpeta de backend.
3. En cada servicio, configura las **Environment Variables**:
   - `DATABASE_URL`: Tu URL de PostgreSQL.
   - `STRIPE_WEBHOOK_SECRET`: El secreto que te da Stripe al configurar el webhook.
4. Railway te dará una URL (ej: `api-filecleaner.railway.app`). Copia esta URL y ponla como `NEXT_PUBLIC_API_URL` en el frontend de Vercel correspondiente.

---

## 4. Configuración de Stripe
Para cada producto:
1. Ve al Dashboard de Stripe -> Developers -> Webhooks.
2. Añade un endpoint: `https://tu-api-en-railway.app/stripe/webhook`.
3. Selecciona los eventos: `checkout.session.completed`, `customer.subscription.deleted`.

---

## ✅ Resumen de Proyectos y URLs

| Producto | Package Name | Vercel Project | Production URL |
|---|---|---|---|
| Main Site | `devforge-site` | `devforge-empire` | devforge-empire.vercel.app |
| File Cleaner | `filecleaner` | `file-cleaner` | file-cleaner-ten.vercel.app |
| Invoice Follow | `invoicefollow` | `invoice-follow` | invoice-follow.vercel.app |
| Price Tracker | `pricetrackr` | `price-trackr` | price-trackr-delta.vercel.app |
| Webhook Monitor | `webhookmonitor` | `webhook-monitor` | webhook-monitor.vercel.app |
| Feedback Lens | `feedbacklens` | `feedback-lens` | feedback-lens-eight.vercel.app |

### Backend Ports (Railway)
| Producto | Carpeta Backend | Port |
|---|---|---|
| File Cleaner | `apps/filecleaner/backend` | 8001 |
| Invoice Follow | `apps/invoicefollow/backend` | 8002 |
| Price Tracker | `apps/pricetrackr/backend` | 8003 |
| Webhook Monitor | `apps/webhookmonitor/backend` | 8004 |
| Feedback Lens | `apps/feedbacklens/backend` | 8005 |

