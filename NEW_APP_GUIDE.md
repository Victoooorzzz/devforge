# Guía de Creación de Nuevos Micro-SaaS (Monorepo DevForge)

Esta guía detalla los pasos exactos para replicar la estructura de un Micro-SaaS dentro del monorepo DevForge. Sigue este checklist para lanzar una nueva app en minutos cumpliendo con los estándares de despliegue y arquitectura actuales.

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
    │       │   └── page.tsx (¡DEBE usar <Suspense>!)
    │       ├── globals.css
    │       ├── layout.tsx (Configuración de Color Accent)
    │       └── page.tsx (Landing Page)
    ├── next.config.mjs
    ├── package.json
    ├── vercel.json
    ├── postcss.config.mjs
    ├── tailwind.config.ts
    └── tsconfig.json
```

---

## 2. Archivos de Configuración (Copiar y Pegar)

### `package.json`
Usa las versiones fijas para garantizar compatibilidad entre apps.
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
    "next": "^14.2.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "lucide-react": "0.378.0",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.6.1"
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

### `next.config.mjs`
**Crucial:** Se debe usar `output: "export"` para facilitar el despliegue local desde Windows (evita errores de symlinks/EPERM).
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@devforge/core", "@devforge/ui"],
  output: "export",
  images: {
    unoptimized: true, // Requerido para output: export
    remotePatterns: [{ protocol: "https", hostname: "images.unsplash.com" }],
  },
};
export default nextConfig;
```

### `vercel.json`
Configura el build para que Vercel sepa que es una exportación estática.
```json
{
  "buildCommand": "next build",
  "outputDirectory": "out"
}
```

---

## 3. Desarrollo de Componentes Críticos

### `register/page.tsx` (Regla de Oro de Next.js 14)
Al usar `useSearchParams()`, Next.js 14 requiere envolver el componente en un `<Suspense>` para poder realizar el build estático.
```tsx
import { Suspense } from "react";
import RegisterForm from "@/components/RegisterForm";

export default function RegisterPage() {
  return (
    <Suspense fallback={<div>Cargando...</div>}>
      <RegisterForm />
    </Suspense>
  );
}
```

### `layout.tsx` (Root)
Define el color de marca de la nueva app.
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
Usa los métodos de `@devforge/core` correctamente.

1.  **Registro**: El método `auth.register` ahora recibe un objeto:
    ```typescript
    await auth.register({
      email,
      password,
      fullName,
      trial: true,
      plan: "pro"
    });
    ```
2.  **Protección**: Usa el middleware o verifica el token JWT mediante `auth.getSession()`.

---

## 5. Despliegue (Estrategia Local Segura)

Para evitar errores de permisos en Windows, el despliegue se hace mediante build local y subida del pre-built:

1.  **Linkear el proyecto** (solo la primera vez):
    ```bash
    cd apps/[nombre-app]/frontend
    vercel link --yes
    ```

2.  **Configurar Framework** (asegúrate de que en `.vercel/project.json` el framework sea `null` para que use el `out` folder):
    *   `"framework": null`
    *   `"outputDirectory": "out"`

3.  **Build y Deploy**:
    ```bash
    vercel build --prod --yes
    vercel deploy --prebuilt --prod --yes
    ```

---

## 6. Variables de Entorno
Asegúrate de configurar en el panel de Vercel:
- `NEXT_PUBLIC_API_URL`: URL del backend de producción.
- `NEXT_PUBLIC_APP_URL`: URL de la propia aplicación.
