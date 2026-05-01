import type { Metadata } from "next";
import { generateMetadata as seoMetadata } from "@devforge/core";
import "@devforge/ui/styles/globals.css";

export const metadata: Metadata = seoMetadata({
  title: "FeedbackLens — AI Sentiment Analysis for Your Product",
  description: "Analyze customer feedback with AI. Detect sentiment, extract themes, and understand your users better. Start free, no credit card required.",
  url: "https://feedbacklens.devforgeapp.pro",
  productName: "FeedbackLens",
  keywords: ["feedback analysis", "sentiment analysis", "ai feedback", "customer insights", "saas"],
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <style dangerouslySetInnerHTML={{ __html: `:root { --color-accent: #10B981; --color-accent-dim: #10B98126; --color-accent-glow: #10B98114; }` }} />
      </head>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
