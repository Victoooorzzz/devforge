import type { Metadata } from "next";
import { generateMetadata as seoMetadata } from "@devforge/core";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = seoMetadata({
  title: "FileCleaner - Industrial-grade data cleaning",
  description: "Clean CSV and Excel files instantly. Fix nulls and duplicates with AI. Ideal for data analysts and teams.",
  url: "https://filecleaner.devforgeapp.pro",
  productName: "FileCleaner",
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className} style={{ "--color-accent": "#F59E0B" } as any}>
        {children}
      </body>
    </html>
  );
}
