import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "WebhookMonitor - Real-time Webhook Debugging",
  description: "Monitor, inspect, and replay webhooks with ease and precision.",
};

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
