import React from "react";
import type { DevForgeProduct } from "@devforge/core";
import { DEVFORGE_PRODUCTS } from "@devforge/core";
import Image from "next/image";
import { FeatureComparison } from "./FeatureComparison";
import { IntegrationCard } from "./IntegrationCard";
import { Layout } from "./Layout";
import { PricingTable } from "./PricingTable";
import { ProductDemo } from "./ProductDemos";
import { ProductDemoShell } from "./ProductDemoShell";
import { StatusBadge } from "./StatusBadge";

interface ProductLandingPageProps {
  product: DevForgeProduct;
}

const featureDescriptions: Record<string, Record<string, string>> = {
  filecleaner: {
    "Preview dirty files before processing": "Inspect rows, columns, sample values, and obvious quality issues before spending a run.",
    "Normalize phone, country, currency, and date columns": "Standardize messy regional formats into predictable values that downstream tools can trust.",
    "Find exact and fuzzy duplicates": "Catch repeated records even when casing, spacing, or small typos make them look different.",
    "Validate schema rules and flag anomaly outliers": "Apply required-column rules, type checks, and outlier flags before exporting a clean file.",
    "Strip EXIF metadata and convert image/PDF utility files": "Remove sensitive metadata and convert utility assets without leaving the cleaning workflow.",
    "Export CSV, XLSX, or JSON with a cleaning report": "Download cleaned data plus a report that explains what changed and what needs review.",
  },
  webhookmonitor: {
    "Endpoint management": "Create isolated webhook URLs for providers, environments, clients, or temporary debugging sessions.",
    "Event table and JSON viewer": "Scan incoming requests quickly, then inspect full payloads without digging through server logs.",
    "Headers viewer": "Review provider headers and masked sensitive values when signature or auth failures need context.",
    "Replay and retry": "Send stored payloads back through a workflow after a fix, without asking the provider to resend.",
    "Payload diffing": "Compare event versions side by side so schema changes do not hide inside large JSON bodies.",
    "Forwarding rules": "Route selected events to staging, a teammate, or another endpoint while keeping production capture intact.",
    "Signature validation": "Check provider signatures near the captured request so security failures are easier to reproduce.",
    "Export cURL/Postman": "Hand off a reproducible request to engineering or support without rebuilding the payload manually.",
  },
  feedbacklens: {
    "Manual and source ingestion": "Collect feedback from manual notes, email, GitHub, Canny, Reddit, and X/Twitter in one inbox.",
    "Sentiment and urgency labels": "Separate praise, churn risk, bugs, and urgent reports before they blend into one queue.",
    "Spam detection": "Filter low-signal submissions so roadmap decisions are based on real customer input.",
    "Semantic deduplication": "Group repeated complaints and feature requests even when users describe them differently.",
    "Topic clusters": "Turn scattered feedback into themes that product, support, and engineering can act on together.",
    "GitHub Issue action": "Convert an important cluster into a draft GitHub issue with context already attached.",
    "Weekly digest": "Send a concise summary of themes, volume changes, urgency, and recommended next actions.",
    "Attachment processing": "Extract text-like attachment content where supported so useful context is not lost.",
  },
  pricetrackr: {
    "Tracker list": "Keep monitored URLs, status, last check time, and current price in one scannable workspace.",
    "Price and stock state": "Track current price, previous price, stock changes, and error states for each URL.",
    "History chart": "See price movement over time so drops, spikes, and stale trackers are easy to spot.",
    "Email/webhook alerts": "Notify operators or automation flows when a product crosses a configured threshold.",
    "Custom selector preview": "Tune selectors for difficult pages before a broken scrape becomes silent bad data.",
    "Scrape error pause state": "Pause noisy trackers when a page changes and surface what needs manual review.",
    "Public product pages": "Expose shareable price-history pages for selected tracked items.",
    "Usage quota": "Show active tracker limits and plan gates before a team hits scale friction.",
  },
  invoicefollow: {
    "Invoice list and status board": "Track overdue, pending, paid, disputed, and promised invoices from one cash view.",
    "CSV/XLS import": "Bring existing invoices in bulk instead of retyping customer, amount, and due-date data.",
    "Reminder schedule": "Run planned follow-up sequences while keeping disputed or sensitive invoices out of automation.",
    "Email history": "Review sent reminders and client replies without losing the collection timeline.",
    "NLP reply classification": "Detect promises to pay, disputes, no-reply patterns, and payment confirmations from responses.",
    "Stripe/PayPal state": "Match payment events back to invoice records so reconciled invoices stop getting chased.",
    "Gmail sync": "Connect mailbox context on paid plans so reminders and replies stay in the same workflow.",
    "Weekly financial digest": "Summarize overdue amount, promised cash, disputed count, and next actions each week.",
    "Usage quota": "Keep invoice, email, NLP, connection, and retention limits visible as the workflow grows.",
  },
};

function getFeatureDescription(product: DevForgeProduct, feature: string): string {
  return featureDescriptions[product.slug]?.[feature] || `${feature} is available in the ${product.name} workflow with plan-aware limits.`;
}

export function ProductLandingPage({ product }: ProductLandingPageProps) {
  const relatedProducts = DEVFORGE_PRODUCTS.filter((item) => item.slug !== product.slug).slice(0, 4);
  const proPlan = product.plans.find((plan) => plan.slug === "pro");
  const teamPlan = product.plans.find((plan) => plan.slug === "team");

  return (
    <div style={{ "--color-accent": product.accentColor } as React.CSSProperties}>
      <Layout
        productName={product.name}
        productDomain={product.domain}
        logoSrc="/devforge-logo-white.svg"
        navLinks={[
          { label: "DevForge", href: "https://devforgeapp.pro" },
          { label: "Demo", href: "#demo" },
          { label: "Features", href: "#features" },
          { label: "Pricing", href: "#pricing" },
          { label: "FAQ", href: "#faq" },
        ]}
        ctaText="Start free"
        ctaHref="/register?plan=free"
      >
        <section className="relative overflow-hidden py-16 md:py-24">
          <div className="section-container grid gap-10 lg:grid-cols-[1fr_420px] lg:items-center">
            <div>
              <div className="mb-5 flex flex-wrap items-center gap-2">
                <StatusBadge tone={product.status === "live" ? "success" : "accent"}>
                  {product.status === "live" ? "Live product" : "Beta pilot: direct feedback"}
                </StatusBadge>
                <StatusBadge tone="neutral">{product.category}</StatusBadge>
                <StatusBadge tone="accent">{proPlan?.priceLabel || "$9.99"} Pro</StatusBadge>
              </div>
              <h1 className="heading-display text-4xl md:text-6xl">
                {product.name}
              </h1>
              <p className="mt-5 max-w-2xl text-lg leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                {product.headline}
              </p>
              <p className="mt-4 max-w-2xl text-base leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                {product.description}
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <a href="/register?plan=free" className="btn-primary">Start free</a>
                <a href="#demo" className="btn-secondary">Try public demo</a>
                <a href="/login" className="btn-ghost">Open dashboard</a>
              </div>
            </div>

            <div className="surface-card-raised border border-white/10 p-5">
              <div className="flex items-center gap-3">
                <Image src="/devforge-logo-white.svg" alt="DevForge" width={126} height={28} className="h-7 w-auto" style={{ width: "auto", height: "auto" }} priority />
                <div>
                  <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Product brief</p>
                  <h2 className="text-lg font-semibold" style={{ color: "var(--color-text)" }}>{product.shortName}</h2>
                </div>
              </div>
              <div className="mt-5 space-y-4">
                {[
                  ["Problem", product.problem],
                  ["Solution", product.solution],
                  ["Built for", product.audience],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-md bg-black/30 p-4">
                    <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>{label}</p>
                    <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <ProductDemoShell title={product.demoTitle} description={product.demoDescription}>
          <ProductDemo slug={product.slug} />
        </ProductDemoShell>

        <section id="features" className="py-16 md:py-20" style={{ backgroundColor: "var(--color-surface)" }}>
          <div className="section-container">
            <div className="mb-8 max-w-3xl">
              <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>Workflow</p>
              <h2 className="heading-section mt-3 text-3xl md:text-4xl">Everything the real dashboard is built around</h2>
              <p className="mt-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                Public demos stay safe, but the feature set mirrors the production backend paths, plan limits, retention, and upgrade gates.
              </p>
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {product.features.map((feature) => (
                <IntegrationCard key={feature} name={feature} description={getFeatureDescription(product, feature)} status="Included" tone="accent" />
              ))}
            </div>
          </div>
        </section>

        <section className="py-16 md:py-20">
          <div className="section-container grid gap-8 lg:grid-cols-[0.85fr_1.15fr]">
            <div>
              <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>Use cases</p>
              <h2 className="heading-section mt-3 text-3xl">Where teams use it</h2>
              <p className="mt-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                The product is intentionally narrow: it targets repeated operations where teams lose time every week.
              </p>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {product.useCases.map((useCase) => (
                <div key={useCase} className="surface-card-raised border border-white/10 p-4">
                  <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>{useCase}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="pricing" className="py-16 md:py-20" style={{ backgroundColor: "var(--color-surface)" }}>
          <div className="section-container">
            <div className="mb-8 max-w-3xl">
              <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>Pricing</p>
              <h2 className="heading-section mt-3 text-3xl md:text-4xl">Free, Pro, and Team plans</h2>
              <p className="mt-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                Start with Free, move to Pro at {proPlan?.priceLabel || "$9.99"}/month, or use Team at {teamPlan?.priceLabel || "$49"}/month when higher limits and shared workflows matter.
              </p>
            </div>
            <PricingTable product={product} />
          </div>
        </section>

        <section className="py-16 md:py-20">
          <div className="section-container">
            <div className="mb-8 max-w-3xl">
              <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>Plan comparison</p>
              <h2 className="heading-section mt-3 text-3xl">Limits without surprises</h2>
            </div>
            <FeatureComparison product={product} />
          </div>
        </section>

        <section id="faq" className="py-16 md:py-20" style={{ backgroundColor: "var(--color-surface)" }}>
          <div className="section-container grid gap-8 lg:grid-cols-[0.75fr_1.25fr]">
            <div>
              <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>FAQ</p>
              <h2 className="heading-section mt-3 text-3xl">Before you sign up</h2>
            </div>
            <div className="space-y-3">
              {product.faq.map((item) => (
                <details key={item.question} className="surface-card-raised border border-white/10 p-4">
                  <summary className="cursor-pointer text-sm font-semibold" style={{ color: "var(--color-text)" }}>{item.question}</summary>
                  <p className="mt-3 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{item.answer}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className="py-12 md:py-16">
          <div className="section-container">
            <details className="surface-card-raised border border-white/10 p-5">
              <summary className="cursor-pointer list-none">
                <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>DevForge suite</p>
                <h2 className="heading-section mt-3 text-3xl">Other tools in the same stack</h2>
              </summary>
              <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {relatedProducts.map((item) => (
                  <a key={item.slug} href={item.url} className="surface-card-raised border border-white/10 p-4 transition hover:border-white/20">
                    <StatusBadge tone={item.status === "live" ? "success" : "neutral"}>{item.status === "live" ? "Live" : "Beta pilot"}</StatusBadge>
                    <h3 className="mt-4 text-lg font-semibold" style={{ color: "var(--color-text)" }}>{item.name}</h3>
                    <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{item.description}</p>
                  </a>
                ))}
              </div>
            </details>
          </div>
        </section>
      </Layout>
    </div>
  );
}
