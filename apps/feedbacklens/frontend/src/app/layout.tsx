import type { Metadata } from "next";
import { GoogleAnalyticsScript, generateMetadata as seoMetadata, generateSoftwareAppJsonLd, getProduct } from "@devforge/core";
import { Inter } from "next/font/google";
import "@devforge/ui/styles/globals.css";

const inter = Inter({ subsets: ["latin"] });
const product = getProduct("feedbacklens");

export const metadata: Metadata = seoMetadata({
  title: product.seoTitle,
  description: product.seoDescription,
  url: product.url,
  productName: product.name,
  keywords: product.keywords,
  tldr: product.description,
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const jsonLd = generateSoftwareAppJsonLd({
    name: product.name,
    description: product.seoDescription,
    url: product.url,
    price: product.plans.find((plan) => plan.slug === "pro")?.price || 9.99,
    category: "DeveloperApplication",
  });

  return (
    <html lang="en">
      <head>
        <GoogleAnalyticsScript />
        <style dangerouslySetInnerHTML={{ __html: `:root { --color-accent: ${product.accentColor}; --color-accent-dim: ${product.accentColor}26; --color-accent-glow: ${product.accentColor}14; }` }} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className={`${inter.className} antialiased`}>{children}</body>
    </html>
  );
}
