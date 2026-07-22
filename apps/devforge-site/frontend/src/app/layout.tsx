import type { Metadata } from "next";
import { DEVFORGE_SUITE, generateMetadata as seoMetadata, generateOrganizationJsonLd } from "@devforge/core";
import { Chakra_Petch, Inter, Oxanium } from "next/font/google";
import "@devforge/ui/styles/globals.css";

const inter = Inter({ subsets: ["latin"], weight: ["300", "400", "500"], variable: "--font-inter" });
const oxanium = Oxanium({ subsets: ["latin"], weight: ["300", "400", "600", "700", "800"], variable: "--font-oxanium" });
const chakra = Chakra_Petch({ subsets: ["latin"], weight: ["300", "400", "600", "700"], variable: "--font-chakra" });

export const metadata: Metadata = seoMetadata({
  title: "DevForge - Four micro-SaaS tools for developers and operators",
  description: DEVFORGE_SUITE.description,
  url: DEVFORGE_SUITE.url,
  productName: DEVFORGE_SUITE.name,
  keywords: ["micro saas tools", "developer tools", "file cleaner", "webhook monitor", "feedback analysis", "price tracker", "invoice reminders"],
  tldr: DEVFORGE_SUITE.headline,
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${oxanium.variable} ${chakra.variable}`}>
      <head>
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
          body { font-family: var(--font-inter), sans-serif; font-size: 15px; line-height: 1.6; }
          h1, h2, h3, h4, h5, h6, .heading-display, .heading-section { font-family: var(--font-oxanium), sans-serif; letter-spacing: 0.05em; text-transform: uppercase; }
          .badge, .font-mono { font-family: var(--font-chakra), sans-serif; letter-spacing: 0.15em; text-transform: uppercase; }
          button, .btn-primary, .btn-secondary, .btn-ghost { font-family: var(--font-chakra), sans-serif; letter-spacing: 0.15em; text-transform: uppercase; border-radius: 2px; }
        ` }} />
        <script defer data-domain="devforgeapp.pro" src="https://plausible.io/js/script.js" />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(generateOrganizationJsonLd()) }} />
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}
