// apps/template/frontend/src/app/layout.tsx

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { generateMetadata as seoMetadata } from "@devforge/core";
import { product } from "@/config/product";
import "@devforge/ui/styles/globals.css";

const inter = Inter({ subsets: ["latin"] });

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
    <html lang="en">
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
                url: "https://devforgeapp.pro",
              },
            }),
          }}
        />
      </head>
      <body className={`${inter.className} antialiased`}>{children}</body>
    </html>
  );
}
