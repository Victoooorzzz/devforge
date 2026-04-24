import type { Metadata } from "next";
import { generateMetadata as seoMetadata, generateOrganizationJsonLd } from "@devforge/core";
import "@devforge/ui/styles/globals.css";

export const metadata: Metadata = seoMetadata({
  title: "DevForge — Indie SaaS Tools for Developers & Freelancers",
  description: "5 micro-products that solve real problems. File management, invoice tracking, price monitoring, webhook debugging, and AI feedback analysis. Built by one developer, used by thousands.",
  url: "https://devforge.io",
  productName: "DevForge",
  keywords: ["saas tools", "developer tools", "micro saas", "indie maker", "devforge"],
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <style dangerouslySetInnerHTML={{ __html: `:root { --color-accent: #6366F1; --color-accent-dim: #6366F126; --color-accent-glow: #6366F114; }` }} />
        <script defer data-domain="devforge.io" src="https://plausible.io/js/script.js" />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(generateOrganizationJsonLd()) }} />
      </head>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
