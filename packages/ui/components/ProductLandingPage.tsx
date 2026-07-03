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
    "Header mapping": "Rename messy columns into stable database-friendly fields before your import sees them.",
    "Duplicate detection": "Catch repeated customers, invoices, SKUs, and emails before they create bad records.",
    "Format normalization": "Standardize dates, currency, booleans, casing, and empty values.",
    "Review before export": "Approve changes before downloading the cleaned file.",
    "Cleanup report": "Export a summary of every change made to the file.",
    "EXIF and utility cleanup": "Strip sensitive metadata and convert utility files when cleanup is not just tabular.",
    "Preview dirty files before processing": "Inspect rows, columns, sample values, and obvious quality issues before spending a run.",
    "Normalize phone, country, currency, and date columns": "Standardize messy regional formats into predictable values that downstream tools can trust.",
    "Find exact and fuzzy duplicates": "Catch repeated records even when casing, spacing, or small typos make them look different.",
    "Validate schema rules and flag anomaly outliers": "Apply required-column rules, type checks, and outlier flags before exporting a clean file.",
    "Strip EXIF metadata and convert image/PDF utility files": "Remove sensitive metadata and convert utility assets without leaving the cleaning workflow.",
    "Export CSV, XLSX, or JSON with a cleaning report": "Download cleaned data plus a report that explains what changed and what needs review.",
  },
  webhookmonitor: {
    "Payload capture": "Store request bodies with headers, timestamps, and delivery attempts.",
    "Replay safely": "Retry one event or a filtered batch without losing the original context.",
    "Failure timeline": "See exactly when the delivery failed, retried, timed out, or recovered.",
    "Signature checks": "Track whether webhook signatures passed, failed, or were missing.",
    "Endpoint health": "Know which endpoints are failing before customers report it.",
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
    "Theme clustering": "Group scattered feedback into product areas without losing the original messages.",
    "Duplicate detection": "Link repeated complaints across Canny, GitHub, email, and support notes.",
    "Urgency scoring": "Separate loud feedback from feedback that blocks revenue or retention.",
    "Digest generation": "Send weekly summaries your product team can actually act on.",
    "Human review": "Keep low-confidence classifications visible instead of pretending the model is always right.",
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
    "Tracked URLs": "Monitor competitor product, plan, or pricing pages from one watchlist.",
    "Stock shifts": "Know when a price drop matters less because inventory is low or unavailable.",
    "Change history": "See how prices moved over days or weeks, not just the latest number.",
    "Alert rules": "Trigger alerts only when movement crosses your threshold.",
    "Decision notes": "Attach context so your team remembers why a price was ignored or reviewed.",
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
    "Reminder schedules": "Create polite follow-up sequences based on due date and invoice status.",
    "Message preview": "Review subject lines, tone, and payment links before reminders go out.",
    "Client replies": "Pause automation when a client responds or disputes an invoice.",
    "Partial payments": "Track remaining balances instead of treating every invoice as paid or unpaid.",
    "Reconciliation notes": "Keep payment status, follow-up history, and owner notes in one place.",
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

function MiniIcon({ type }: { type: "problem" | "solution" | "audience" }) {
  const paths = {
    problem: <path d="M12 8v4m0 4h.01M4.9 19h14.2L12 4 4.9 19Z" />,
    solution: <path d="M9 12l2 2 4-5M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z" />,
    audience: <path d="M16 19v-1.5A3.5 3.5 0 0 0 12.5 14h-5A3.5 3.5 0 0 0 4 17.5V19m12-8a3 3 0 1 0 0-6m-6 6a3 3 0 1 0 0-6m10 14v-1a3 3 0 0 0-2-2.83" />,
  };

  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths[type]}
    </svg>
  );
}

function FeatureIcon({ feature }: { feature: string }) {
  const lower = feature.toLowerCase();
  let path = <path d="M4 12h16M12 4v16" />;

  if (lower.includes("preview") || lower.includes("viewer") || lower.includes("chart")) {
    path = <><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" /><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" /></>;
  } else if (lower.includes("metadata") || lower.includes("exif") || lower.includes("signature") || lower.includes("validation")) {
    path = <><path d="M7 11V8a5 5 0 0 1 10 0v3" /><path d="M6 11h12v9H6z" /></>;
  } else if (lower.includes("duplicate") || lower.includes("dedup") || lower.includes("diff")) {
    path = <><path d="M8 8h11v11H8z" /><path d="M5 5h11" /><path d="M5 5v11" /></>;
  } else if (lower.includes("export") || lower.includes("curl") || lower.includes("postman")) {
    path = <><path d="M12 3v12" /><path d="m7 10 5 5 5-5" /><path d="M5 21h14" /></>;
  } else if (lower.includes("normalize") || lower.includes("rules") || lower.includes("selector")) {
    path = <><path d="M4 7h16" /><path d="M7 7v10" /><path d="M17 7v10" /><path d="M4 17h16" /></>;
  } else if (lower.includes("alert") || lower.includes("digest") || lower.includes("reminder")) {
    path = <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9Z" /><path d="M10 21h4" /></>;
  } else if (lower.includes("replay") || lower.includes("retry") || lower.includes("sync")) {
    path = <><path d="M21 12a9 9 0 0 1-15.5 6.2" /><path d="M3 12A9 9 0 0 1 18.5 5.8" /><path d="M18 2v4h-4" /><path d="M6 22v-4h4" /></>;
  }

  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {path}
    </svg>
  );
}

function ProductUniqueSection({ product }: { product: DevForgeProduct }) {
  return (
    <section className="py-16 md:py-20">
      <div className="section-container">
        <div className="mb-8 max-w-3xl">
          <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>{product.uniqueSection.eyebrow}</p>
          <h2 className="heading-section mt-3 text-3xl md:text-4xl">{product.uniqueSection.title}</h2>
          <p className="mt-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{product.uniqueSection.description}</p>
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          {product.uniqueSection.blocks.map((block) => (
            <div key={block.label} className="surface-card-raised border border-white/10 p-5">
              <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>{block.label}</p>
              <p className="mt-3 whitespace-pre-line font-mono text-xs leading-relaxed" style={{ color: "var(--color-text)" }}>{block.body}</p>
            </div>
          ))}
        </div>
        {product.uniqueSection.badges?.length ? (
          <div className="mt-5 flex flex-wrap gap-2">
            {product.uniqueSection.badges.map((badge) => (
              <StatusBadge key={badge} tone="accent">{badge}</StatusBadge>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
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
              <p className="mt-4 max-w-2xl rounded-md border border-white/10 bg-black/25 p-4 text-sm leading-relaxed" style={{ color: "var(--color-text)" }}>
                {product.founderNote}
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <a href="/register?plan=free" className="btn-primary">Start free</a>
                <a href="#demo" className="btn-secondary">Try public demo</a>
                <a href="/login" className="btn-outline">Open dashboard</a>
              </div>
            </div>

            <div className="surface-card-raised border border-white/10 p-5">
              <div className="flex items-center gap-3">
                <Image src="/devforge-logo-white.svg" alt="DevForge" width={126} height={28} priority />
                <div>
                  <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Product brief</p>
                  <h2 className="text-lg font-semibold" style={{ color: "var(--color-text)" }}>{product.shortName}</h2>
                </div>
              </div>
              <div className="mt-5 space-y-4">
                {product.briefCards.map((card, index) => (
                  <div key={card.label} className="rounded-md bg-black/30 p-4">
                    <p className="flex items-center gap-2 text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>
                      <MiniIcon type={index === 0 ? "problem" : index === 1 ? "solution" : "audience"} />
                      {card.label}
                    </p>
                    <h3 className="mt-2 text-sm font-semibold" style={{ color: "var(--color-text)" }}>{card.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{card.body}</p>
                  </div>
                ))}
                <div className="rounded-md border border-white/10 bg-black/20 p-4">
                  <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Product signal</p>
                  <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-text)" }}>{product.proofPoint}</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <ProductDemoShell title={product.demoTitle} description={product.demoDescription}>
          <ProductDemo slug={product.slug} />
        </ProductDemoShell>

        <ProductUniqueSection product={product} />

        <section id="features" className="py-16 md:py-20" style={{ backgroundColor: "var(--color-surface)" }}>
          <div className="section-container">
            <div className="mb-8 max-w-3xl">
              <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>Workflow</p>
              <h2 className="heading-section mt-3 text-3xl md:text-4xl">{product.featureSectionTitle}</h2>
              <p className="mt-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                {product.featureSectionDescription}
              </p>
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {product.features.map((feature) => (
                <IntegrationCard key={feature} name={feature} description={getFeatureDescription(product, feature)} icon={<FeatureIcon feature={feature} />} />
              ))}
            </div>
          </div>
        </section>

        <section className="py-16 md:py-20">
          <div className="section-container grid gap-8 lg:grid-cols-[0.85fr_1.15fr]">
            <div>
              <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>Use cases</p>
              <h2 className="heading-section mt-3 text-3xl">{product.useCaseSectionTitle}</h2>
              <p className="mt-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                {product.useCaseSectionDescription}
              </p>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {product.useCases.map((useCase) => (
                <div key={useCase} className="use-case-card surface-card-raised border border-white/10 p-4">
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
              <h2 className="heading-section mt-3 text-3xl md:text-4xl">{product.pricingSectionTitle}</h2>
              <p className="mt-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                {product.pricingSectionDescription} Pro starts at {proPlan?.priceLabel || "$9.99"}/month and Team at {teamPlan?.priceLabel || "$49"}/month.
              </p>
            </div>
            <PricingTable product={product} />
          </div>
        </section>

        <section className="py-16 md:py-20">
          <div className="section-container">
            <div className="mb-8 max-w-3xl">
              <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>Plan comparison</p>
              <h2 className="heading-section mt-3 text-3xl">{product.comparisonSectionTitle}</h2>
            </div>
            <FeatureComparison product={product} />
          </div>
        </section>

        <section id="faq" className="py-16 md:py-20" style={{ backgroundColor: "var(--color-surface)" }}>
          <div className="section-container grid gap-8 lg:grid-cols-[0.75fr_1.25fr]">
            <div>
              <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>FAQ</p>
              <h2 className="heading-section mt-3 text-3xl">{product.faqSectionTitle}</h2>
            </div>
            <div className="space-y-3">
              {product.faq.map((item) => (
                <details key={item.question} className="faq-accordion surface-card-raised border border-white/10 p-4">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-semibold" style={{ color: "var(--color-text)" }}>
                    <span>{item.question}</span>
                    <span className="faq-chevron" aria-hidden="true">
                      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <path d="m9 6 6 6-6 6" />
                      </svg>
                    </span>
                  </summary>
                  <div className="faq-answer">
                    <p className="pt-3 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{item.answer}</p>
                  </div>
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
                <h2 className="heading-section mt-3 text-3xl">{product.relatedSectionTitle}</h2>
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
