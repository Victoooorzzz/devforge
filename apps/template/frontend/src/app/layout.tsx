// apps/template/frontend/src/app/layout.tsx

import type { Metadata } from "next";
import localFont from "next/font/local";
import { generateMetadata as seoMetadata } from "@devforge/core";
import { product } from "@/config/product";
import "@devforge/ui/styles/globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
  display: "swap",
});

const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
  display: "swap",
});

export const metadata: Metadata = seoMetadata({
  title: product.seoTitle,
  description: product.seoDescription,
  url: product.url,
  productName: product.name,
  keywords: [product.keyword, "devforge", "saas tool"],
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <head>
        <style
          dangerouslySetInnerHTML={{
            __html: `:root { --color-accent: ${product.accentColor}; --color-accent-dim: ${product.accentColor}26; --color-accent-glow: ${product.accentColor}14; }`,
          }}
        />
        {product.plausibleDomain && (
          <script
            defer
            data-domain={product.plausibleDomain}
            src="https://plausible.io/js/script.js"
          />
        )}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              name: product.name,
              description: product.seoDescription,
              url: product.url,
              applicationCategory: "DeveloperApplication",
              operatingSystem: "Web",
              offers: {
                "@type": "Offer",
                price: product.pricing.price,
                priceCurrency: "USD",
                availability: "https://schema.org/InStock",
              },
              creator: {
                "@type": "Organization",
                name: "DevForge",
                url: "https://devforge.io",
              },
            }),
          }}
        />
      </head>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
