import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FileCleaner - Automated Storage Management",
  description: "Keep your storage clean and organized with automated file cleanup and classification.",
};

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
