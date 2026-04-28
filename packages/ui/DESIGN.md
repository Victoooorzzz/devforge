# DevForge Design System — "The Monochrome Architect"

> Generated from Stitch MCP, Project ID: 8436566603512898551
> Design System Asset: assets/4837b9f1aa1a4a84af4f30faf0f0c85f

## 1. Overview & Creative North Star

This design system is built for the high-performance developer environment — a space where technical precision meets editorial elegance. Our Creative North Star is **"The Monochrome Architect."**

We emphasize **tonal depth and intentional asymmetry**. We treat the UI as a high-end IDE: high-contrast for readability, yet sophisticated through layered surfaces.

## 2. Color & Surface Philosophy

The palette is rooted in deep obsidian tones with surgical application of the product accent color.

### Surface Hierarchy (Tonal Layering)

| Token | Hex | Usage |
|-------|-----|-------|
| `--color-bg` | `#0A0A0A` | Page canvas |
| `--color-surface` | `#111111` | Primary content containers |
| `--color-surface-raised` | `#1C1B1B` | Elevated containers, sidebars |
| `--color-surface-high` | `#2A2A2A` | Modals, popovers, dropdowns |
| `--color-surface-bright` | `#353534` | Hover states, active items |

### Text Hierarchy

| Token | Hex | Usage |
|-------|-----|-------|
| `--color-text` | `#F5F5F5` | Headlines, primary content |
| `--color-text-secondary` | `#A3A3A3` | Body text, descriptions |

### Accent Colors (Per Product)

| Product | Accent | CSS Variable Override |
|---------|--------|----------------------|
| Webhook Monitor | `#6366F1` | `--color-accent: #6366F1` |
| File Cleaner | `#F59E0B` | `--color-accent: #F59E0B` |
| Invoice Follow-up | `#10B981` | `--color-accent: #10B981` |
| Price Tracker | `#EF4444` | `--color-accent: #EF4444` |
| Feedback Analyzer | `#8B5CF6` | `--color-accent: #8B5CF6` |

### Rules

- **No-Line Rule**: Standard 1px solid borders are prohibited for sectioning. Use background color shifts between surface tokens.
- **Ghost Border**: When a border is required for accessibility, use `--color-border` at 15% opacity.
- **Glass & Gradient**: CTAs use accent gradient (135deg). Nav uses `backdrop-filter: blur(12px)` with 80% surface opacity.

## 3. Typography

| Role | Font | Weight | Letter Spacing |
|------|------|--------|----------------|
| Display/Headlines | Geist | 700 | -0.02em |
| Body | Geist | 400 | 0em |
| Labels/Meta | Geist | 500 | 0.025em |
| Code/Data/Prices | Geist Mono | 400 | 0em |

## 4. Elevation & Depth

- **Tonal Layering**: Depth via stacking surface tokens. No drop shadows for flat elements.
- **Ambient Shadows**: Floating elements use: `0px 24px 48px rgba(0,0,0,0.4), 0px 0px 4px rgba(accent, 0.08)`
- **Glassmorphism**: Navigation bars use `surface` at 80% opacity with `blur(12px)`.

## 5. Components

### Buttons
- **Primary**: Accent gradient, white text, `radius-sm`
- **Secondary**: `surface-high` background, no border, text color
- **Ghost**: Transparent, accent text, accent-dim hover

### Input Fields
- Default: `--color-bg` background (inset feel)
- Focus: Accent border with 2px outer glow

### Cards
- Use `surface` or `surface-raised` background
- No line dividers between list items
- 12px spacing or hover shift for separation

## 6. Spacing

Based on a 4px grid: 4, 8, 12, 16, 24, 32, 40, 48, 64, 80, 96px.

## 7. Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `0.375rem` | Buttons, inputs, badges |
| `--radius-md` | `0.5rem` | Cards, containers |
| `--radius-lg` | `0.75rem` | Large containers, modals |
hola