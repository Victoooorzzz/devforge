import type { Metadata } from "next";
import { generateMetadata as seoMetadata } from "@devforge/core";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = seoMetadata({
  title: "PriceTrackr - Real-time market intelligence",
  description: "Monitor competitor prices in background. Get alerted instantly on price changes. Built for e-commerce owners.",
  url: "https://pricetrackr.devforgeapp.pro",
  productName: "PriceTrackr",
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className} style={{ "--color-accent": "#EF4444" } as any}>
        {children}
      </body>
    </html>
  );
}
