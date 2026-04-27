import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "PriceTrackr - Competitor Price Monitoring",
  description: "Track competitor prices in real-time and stay ahead of the market.",
};

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
