# Guía de Creación de Nuevos Micro-SaaS (Monorepo DevForge)

Esta guía detalla los pasos exactos para replicar la estructura de un Micro-SaaS dentro del monorepo DevForge. Sigue este checklist para lanzar una nueva app en minutos.

---

## 1. Estructura de Carpetas
Crea la siguiente jerarquía dentro de `apps/`:

```text
apps/[nombre-app]/
└── frontend/
    ├── src/
    │   └── app/
    │       ├── dashboard/
    │       │   ├── layout.tsx (Protección de ruta)
    │       │   └── page.tsx
    │       ├── login/
    │       │   └── page.tsx
    │       ├── register/
    │       │   └── page.tsx
    │       ├── globals.css
    │       ├── layout.tsx (Configuración de Color Accent)
    │       └── page.tsx (Landing Page)
    ├── next.config.js
    ├── package.json
    ├── postcss.config.mjs
    ├── tailwind.config.ts
    └── tsconfig.json
```

---

## 2. Archivos de Configuración (Copiar y Pegar)

### `package.json`
Asegúrate de incluir las dependencias del workspace y fijar Tailwind a la v3.
```json
{
  "name": "@devforge/[nombre-app]",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "@devforge/core": "workspace:*",
    "@devforge/ui": "workspace:*",
    "next": "14.1.0",
    "react": "^18",
    "react-dom": "^18",
    "lucide-react": "^0.344.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "autoprefixer": "^10.0.1",
    "postcss": "^8",
    "tailwindcss": "^3.4.1",
    "typescript": "^5"
  }
}
```

### `next.config.js`
**Crucial:** Debes transpilar los paquetes compartidos.
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@devforge/core", "@devforge/ui"],
  images: {
    remotePatterns: [{ protocol: "https", hostname: "images.unsplash.com" }],
  },
};
module.exports = nextConfig;
```

### `tailwind.config.ts`
Extiende el tema base de DevForge.
```typescript
import type { Config } from "tailwindcss";
import sharedConfig from "@devforge/ui/tailwind.config";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "../../packages/ui/src/**/*.{js,ts,jsx,tsx,mdx}", // Escanear UI compartida
  ],
  presets: [sharedConfig],
  theme: {
    extend: {
      colors: {
        accent: "var(--color-accent)", // Color dinámico por app
      },
    },
  },
};
export default config;
```

---

## 3. Integración con el Sistema de Diseño

### `globals.css`
Importa la base compartida y define tus capas locales si es necesario.
```css
@import "@devforge/ui/styles/globals.css";

@tailwind base;
@tailwind components;
@tailwind utilities;
```

### `layout.tsx` (Root)
Define el color de marca de la nueva app usando la variable `--color-accent`.
```tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body style={{ "--color-accent": "#TU_COLOR_HEX" } as any}>
        {children}
      </body>
    </html>
  );
}
```

---

## 4. Checklist de Autenticación
Para que el login/registro funcione, usa los hooks de `@devforge/core`:

1.  **Registro**: En el formulario, envía `trial: true` y el `plan` ("starter" o "pro") al llamar a `auth.register`.
2.  **Dashboard**: El archivo `dashboard/layout.tsx` debe envolver el contenido en un componente de protección o verificar el token JWT almacenado en cookies/localStorage mediante `auth.getSession()`.

---

## 5. Despliegue en Vercel

Desde la raíz del monorepo, ejecuta:
```bash
vercel apps/[nombre-app]/frontend --name [slug-de-la-app]
```

**Configuración en el Panel de Vercel:**
- **Framework Preset**: Next.js
- **Root Directory**: `apps/[nombre-app]/frontend`
- **Environment Variables**: Asegúrate de setear `NEXT_PUBLIC_API_URL` apuntando a tu backend de producción.
