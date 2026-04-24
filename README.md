# DevForge Monorepo

A complete micro-SaaS ecosystem — 5 independent products sharing infrastructure, design system, and billing.

## Architecture

```
devforge/
├── packages/
│   ├── ui/              # @devforge/ui — Design system + 10 React components
│   ├── core/            # @devforge/core — Auth, API client, Stripe, Analytics, SEO
│   └── backend-core/    # Shared FastAPI factory, JWT auth, Stripe webhooks, email
├── apps/
│   ├── template/        # Cloneable reference implementation
│   ├── devforge-site/   # devforge.io portfolio (static export)
│   ├── filecleaner/     # File Cleaner ($9/mo, amber)
│   ├── invoicefollow/   # Invoice Follow-up ($12/mo, emerald)
│   ├── pricetrackr/     # Price Tracker ($15/mo, red)
│   ├── webhookmonitor/  # Webhook Monitor ($19/mo, indigo)
│   └── feedbacklens/    # Feedback Analyzer ($19/mo, violet)
└── .env.example
```

## Quick Start

```bash
# Install dependencies
pnpm install

# Copy environment config
cp .env.example .env
# Edit .env with your credentials

# Run any product frontend
cd apps/webhookmonitor/frontend && pnpm dev

# Run any product backend
cd apps/webhookmonitor/backend && python main.py
```

## Product Backend Ports

| Product | Frontend | Backend |
|---------|----------|---------|
| Template | 3000 | 8000 |
| Portfolio | 3001 | — |
| File Cleaner | 3002 | 8001 |
| Invoice Follow-up | 3003 | 8002 |
| Price Tracker | 3004 | 8003 |
| Webhook Monitor | 3005 | 8004 |
| Feedback Analyzer | 3006 | 8005 |

## Creating a New Product

1. Copy `apps/template` to `apps/your-product`
2. Edit `frontend/src/config/product.ts` (name, accent, pricing, features)
3. Add domain-specific dashboard components in `frontend/src/app/dashboard/`
4. Add domain-specific routes in `backend/main.py`
5. Add to `packages/ui/components/ProductCard.tsx` product list

## Design System

The "Monochrome Architect" design DNA is documented in `packages/ui/DESIGN.md`.

Key rules:
- Products inject accent via `--color-accent` CSS variable (never hardcoded Tailwind utilities)
- No structural 1px borders — use background tonal shifts
- Typography: Geist Sans for UI, Geist Mono for data/prices
- Surface hierarchy: bg → surface → surface-raised → surface-high → surface-bright

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React 18, Tailwind CSS |
| Backend | FastAPI, SQLModel, asyncpg |
| Auth | JWT (bcrypt + python-jose) |
| Payments | Stripe Checkout (hosted redirect) |
| Analytics | Plausible |
| AI | Google Gemini (Feedback Analyzer) |
| Storage | Cloudflare R2 (S3-compatible) |
