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
  tldr?: string;
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
      "ai-friendly": "true",
      "generative-engine-optimization": "true",
      ...(config.tldr ? { "tldr": config.tldr } : { "tldr": description }),
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
  status?: "live" | "beta";
  audience?: string;
  features?: string[];
  plans?: Array<{
    name: string;
    price: number;
    description: string;
    limits: string[];
  }>;
}): Record<string, unknown> {
  const offers = config.plans?.length
    ? config.plans.map((plan) => ({
        "@type": "Offer",
        name: `${config.name} ${plan.name}`,
        price: plan.price,
        priceCurrency: config.currency || "USD",
        description: plan.description,
        availability: "https://schema.org/InStock",
        url: `${config.url}/#pricing`,
        additionalProperty: plan.limits.map((limit) => ({
          "@type": "PropertyValue",
          name: "Plan limit",
          value: limit,
        })),
      }))
    : {
        "@type": "Offer",
        price: config.price,
        priceCurrency: config.currency || "USD",
        availability: "https://schema.org/InStock",
      };

  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "@id": `${config.url}/#software`,
    name: config.name,
    description: config.description,
    url: config.url,
    applicationCategory: config.category || "DeveloperApplication",
    operatingSystem: "Web",
    applicationSuite: "DevForge",
    softwareVersion: config.status === "beta" ? "Beta" : "Production",
    audience: config.audience ? { "@type": "Audience", audienceType: config.audience } : undefined,
    featureList: config.features,
    offers,
    creator: {
      "@type": "Organization",
      "@id": "https://tools.devforgeapp.pro/#organization",
      name: "DevForge",
      url: "https://tools.devforgeapp.pro",
    },
  };
}

export function generateOrganizationJsonLd(): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "DevForge",
    "@id": "https://tools.devforgeapp.pro/#organization",
    url: "https://tools.devforgeapp.pro",
    description: "Four focused micro-SaaS tools for developers, operators, founders, and small teams.",
    sameAs: [],
  };
}
