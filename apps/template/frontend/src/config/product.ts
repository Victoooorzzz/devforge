// apps/template/frontend/src/config/product.ts

// --- TEMPLATE CONTRACT ---
// This is the ONLY file that changes between products (besides dashboard/ and backend/).
// Modify these values when cloning the template for a new product.

export interface Product {
  name: string;
  tagline: string;
  domain: string;
  url: string;
  accentColor: string;
  keyword: string;
  seoTitle: string;
  seoDescription: string;
  navLinks: { label: string; href: string }[];
  hero: {
    badge: string;
    headline: string;
    subtitle: string;
    ctaText: string;
    ctaHref: string;
    secondaryCtaText: string;
    secondaryCtaHref: string;
  };
  features: { title: string; description: string }[];
  pricing: {
    planName: string;
    price: number;
    description: string;
    lsVariantId: string;
    features: { text: string; included: boolean }[];
  };
  testimonials: { quote: string; name: string; role: string }[];
  dashboardNav: { label: string; href: string }[];
  plausibleDomain: string;
}

export const product: Product = {
  // Brand
  name: "Product Name",
  tagline: "Your product tagline goes here",
  domain: "product.io",
  url: "https://product.io",
  accentColor: "#6366F1",

  // SEO
  keyword: "primary keyword for this product",
  seoTitle: "Primary Feature | Product Name by DevForge",
  seoDescription: "A compelling description under 155 characters with the primary keyword included for search optimization.",

  // Navigation
  navLinks: [
    { label: "Features", href: "#features" },
    { label: "Pricing", href: "#pricing" },
  ],

  // Hero
  hero: {
    badge: "Now in Beta",
    headline: "Your Product Headline",
    subtitle: "A two-sentence description of the value proposition that resonates with the target user persona.",
    ctaText: "Start Free Trial",
    ctaHref: "/register",
    secondaryCtaText: "View Demo",
    secondaryCtaHref: "#features",
  },

  // Features
  features: [
    {
      title: "Feature One",
      description: "A clear explanation of what this feature does and why the user should care.",
    },
    {
      title: "Feature Two",
      description: "A clear explanation of what this feature does and why the user should care.",
    },
    {
      title: "Feature Three",
      description: "A clear explanation of what this feature does and why the user should care.",
    },
  ],

  // Pricing
  pricing: {
    planName: "Pro",
    price: 19,
    description: "Everything you need to get started",
    lsVariantId: process.env.NEXT_PUBLIC_LS_VARIANT_ID || "",

    features: [
      { text: "Core feature 1", included: true },
      { text: "Core feature 2", included: true },
      { text: "Core feature 3", included: true },
      { text: "Priority support", included: true },
      { text: "Phase 2 feature", included: false },
    ],
  },

  // Testimonials
  testimonials: [
    {
      quote: "This tool saved me hours every week. The interface is clean and it just works.",
      name: "Alex Chen",
      role: "Full-Stack Developer",
    },
    {
      quote: "Finally a tool that does one thing really well without the bloat.",
      name: "Sarah Kim",
      role: "Freelance Designer",
    },
    {
      quote: "The pricing is fair for solo developers. Highly recommend.",
      name: "Marcus Rivera",
      role: "Indie Maker",
    },
  ],

  // Dashboard navigation
  dashboardNav: [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Settings", href: "/dashboard/settings" },
  ],

  // Analytics
  plausibleDomain: "product.io",
};
