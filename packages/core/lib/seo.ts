// packages/core/lib/seo.ts

import type { Metadata } from "next";

interface SEOConfig {
  title: string;
  description: string;
  url: string;
  ogImage?: string;
  keywords?: string[];
  productName?: string;
  price?: number;
  jsonLd?: Record<string, unknown>;
}

export function generateMetadata(config: SEOConfig): Metadata {
  const {
    title,
    description,
    url,
    ogImage = `${url}/og-image.png`,
    keywords = [],
  } = config;

  return {
    title,
    description,
    keywords,
    metadataBase: new URL(url),
    alternates: {
      canonical: url,
    },
    openGraph: {
      title,
      description,
      url,
      siteName: config.productName || "DevForge",
      images: [
        {
          url: ogImage,
          width: 1200,
          height: 630,
          alt: title,
        },
      ],
      locale: "en_US",
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [ogImage],
      creator: "@devforge",
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        "max-video-preview": -1,
        "max-image-preview": "large",
        "max-snippet": -1,
      },
    },
    other: {
      "author": "DevForge",
    },
  };
}

export function generateSoftwareAppJsonLd(config: {
  name: string;
  description: string;
  url: string;
  price: number;
  currency?: string;
  category?: string;
}): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: config.name,
    description: config.description,
    url: config.url,
    applicationCategory: config.category || "DeveloperApplication",
    operatingSystem: "Web",
    offers: {
      "@type": "Offer",
      price: config.price,
      priceCurrency: config.currency || "USD",
      availability: "https://schema.org/InStock",
    },
    creator: {
      "@type": "Organization",
      name: "DevForge",
      url: "https://devforge.io",
    },
  };
}

export function generateOrganizationJsonLd(): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "DevForge",
    url: "https://devforge.io",
    description: "Indie SaaS Tools for Developers and Freelancers",
    sameAs: [],
  };
}
