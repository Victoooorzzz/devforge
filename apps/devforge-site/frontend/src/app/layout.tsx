import type { Metadata } from "next";
import { generateMetadata as seoMetadata, generateOrganizationJsonLd } from "@devforge/core";
import "@devforge/ui/styles/globals.css";

export const metadata: Metadata = seoMetadata({
  title: "DevForge — Indie SaaS Tools for Developers & Freelancers",
  description: "5 micro-products that solve real problems. File management, invoice tracking, price monitoring, webhook debugging, and AI feedback analysis. Built by one developer, used by thousands.",
  url: "https://devforgeapp.pro",
  productName: "DevForge",
  keywords: ["saas tools", "developer tools", "micro saas", "indie maker", "devforge"],
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Oxanium:wght@300;400;600;700;800&family=Chakra+Petch:wght@300;400;600;700&family=Inter:wght@300;400;500&display=swap" rel="stylesheet" />
        <style dangerouslySetInnerHTML={{ __html: `
          :root { 
            --color-accent: #821346; 
            --color-accent-dim: #82134626; 
            --color-accent-glow: #82134614;
            --color-bg: #0E0C0D;
            --color-surface: #191718;
            --color-surface-raised: #282627;
            --color-surface-high: #383536;
            --color-text: #F9F7F8;
            --color-text-secondary: #7F7A7C;
            --color-border: #282627;
            --radius-sm: 2px;
            --radius-md: 4px;
            --radius-lg: 6px;
          }
          body { font-family: 'Inter', sans-serif; font-size: 15px; line-height: 1.6; }
          h1, h2, h3, h4, h5, h6, .heading-display, .heading-section { font-family: 'Oxanium', sans-serif; letter-spacing: 0.05em; text-transform: uppercase; }
          .badge, .font-mono { font-family: 'Chakra Petch', sans-serif; letter-spacing: 0.15em; text-transform: uppercase; }
          button, .btn-primary, .btn-secondary, .btn-ghost { font-family: 'Chakra Petch', sans-serif; letter-spacing: 0.15em; text-transform: uppercase; border-radius: 2px; }
        ` }} />
        <script defer data-domain="devforgeapp.pro" src="https://plausible.io/js/script.js" />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(generateOrganizationJsonLd()) }} />
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}
