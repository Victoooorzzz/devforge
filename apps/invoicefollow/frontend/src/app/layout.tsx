import type { Metadata } from "next";
import type { CSSProperties } from "react";
import { generateMetadata as seoMetadata, generateSoftwareAppJsonLd, getProduct } from "@devforge/core";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });
const product = getProduct("invoicefollow");

export const metadata: Metadata = seoMetadata({
  title: product.seoTitle,
  description: product.seoDescription,
  url: product.url,
  productName: product.name,
  keywords: product.keywords,
  tldr: product.description,
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
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
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className={inter.className} style={{
        "--color-accent": product.accentColor,
        "--color-accent-dim": `${product.accentColor}26`,
        "--color-accent-glow": `${product.accentColor}14`,
      } as CSSProperties}>
        {children}
      </body>
    </html>
  );
}
