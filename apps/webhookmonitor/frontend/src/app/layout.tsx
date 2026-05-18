import type { Metadata } from "next";
import { generateMetadata as seoMetadata } from "@devforge/core";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = seoMetadata({
  title: "WebhookMonitor - Terminal-grade webhook inspection",
  description: "Intercept, inspect, and replay webhooks. Universal logging for Stripe, GitHub. Made for backend developers.",
  url: "https://webhookmonitor.devforgeapp.pro",
  productName: "WebhookMonitor",
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className} style={{ "--color-accent": "#8B5CF6" } as any}>
        {children}
      </body>
    </html>
  );
}
