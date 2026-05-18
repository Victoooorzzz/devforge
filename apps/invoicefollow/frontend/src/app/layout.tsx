import type { Metadata } from "next";
import { generateMetadata as seoMetadata } from "@devforge/core";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = seoMetadata({
  title: "InvoiceFollow - Automated payment recovery",
  description: "Automate invoice follow-ups and get paid faster. Perfect for freelancers and agencies. Send smart reminders.",
  url: "https://invoicefollow.devforgeapp.pro",
  productName: "InvoiceFollow",
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className} style={{ "--color-accent": "#6366F1" } as any}>
        {children}
      </body>
    </html>
  );
}
