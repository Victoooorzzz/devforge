import { DEVFORGE_PRODUCTS, DEVFORGE_SUITE } from "@devforge/core";
import type { ProductInfo } from "./ProductCard";
import { Layout } from "./Layout";
import { ProductGrid } from "./ProductGrid";
import { StatusBadge } from "./StatusBadge";

const audienceTagsByProduct = {
  filecleaner: ["Dirty CSVs", "Bad imports", "Cleanup reports"],
  webhookmonitor: ["Failed hooks", "Payload evidence", "Replay"],
  feedbacklens: ["Messy feedback", "Duplicates", "Roadmap proof"],
  pricetrackr: ["Price drops", "Stock shifts", "Margin checks"],
  invoicefollow: ["Unpaid invoices", "Polite reminders", "Manual review"],
};

const productCards: ProductInfo[] = DEVFORGE_PRODUCTS.map((product) => ({
  slug: product.slug,
  name: product.name,
  tagline: product.headline,
  domain: product.domain,
  accentColor: product.accentColor,
  price: product.plans.find((plan) => plan.slug === "pro")?.price || 9.99,
  status: product.status,
  problem: undefined,
  solution: undefined,
  audienceTags: audienceTagsByProduct[product.slug],
}));

const suitePlans = [
  {
    name: "Free",
    price: "$0",
    description: "For testing one real workflow before you trust it with production mess.",
    limits: ["Low limits", "One workspace", "Core workflow"],
  },
  {
    name: "Pro",
    price: "$9.99",
    description: "For individual operators running the workflow often enough that manual work hurts.",
    limits: ["More volume", "Longer history", "Exports, alerts, or automation"],
  },
  {
    name: "Team",
    price: "$49",
    description: "For small teams that need shared access, higher limits, and safer collaboration.",
    limits: ["Members", "Permissions", "More retention", "Priority support"],
  },
];

const suiteComparison = [
  { key: "demo", label: "Live demo" },
  { key: "dashboard", label: "Dashboard" },
  { key: "pro", label: "Pro gates" },
  { key: "team", label: "Team scale" },
];

function AvailabilityIcon({ enabled }: { enabled: boolean }) {
  return enabled ? (
    <span className="comparison-icon comparison-icon-yes" aria-label="Included">
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M20 6 9 17l-5-5" />
      </svg>
    </span>
  ) : (
    <span className="comparison-icon comparison-icon-no" aria-label="Not included">
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M18 6 6 18" />
        <path d="m6 6 12 12" />
      </svg>
    </span>
  );
}

export function SuiteHomePage() {
  const liveCount = DEVFORGE_PRODUCTS.filter((product) => product.status === "live").length;

  return (
    <Layout
      productName={DEVFORGE_SUITE.name}
      productDomain={DEVFORGE_SUITE.domain}
      logoSrc="/devforge-logo-white.svg"
      navLinks={[
        { label: "Products", href: "#products" },
        { label: "Plans", href: "#plans" },
        { label: "Comparison", href: "#comparison" },
        { label: "Hire", href: "/hire" },
      ]}
      ctaText="Start free"
      ctaHref="/register?plan=free"
    >
      <section className="py-16 md:py-24">
        <div className="section-container grid gap-10 lg:grid-cols-[1fr_420px] lg:items-center">
          <div>
            <div className="mb-5 flex flex-wrap items-center gap-2">
              <StatusBadge tone="success">4 focused tools</StatusBadge>
              <StatusBadge tone="neutral">Shared auth + billing</StatusBadge>
              <StatusBadge tone="neutral">Built for small teams</StatusBadge>
              <StatusBadge tone="accent">No enterprise theater</StatusBadge>
            </div>
            <h1 className="heading-display text-4xl md:text-6xl">
              {DEVFORGE_SUITE.name}
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
              {DEVFORGE_SUITE.headline}
            </p>
            <p className="mt-4 max-w-2xl text-base leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
              {DEVFORGE_SUITE.description}
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a href="/register?plan=free" className="btn-primary">Start free</a>
              <a href="#plans" className="btn-secondary">Compare plans</a>
              <a href="#products" className="btn-ghost">View products</a>
            </div>
          </div>
          <div className="suite-hero-mockup surface-card-raised border border-white/10 p-5 animate-scale-in">
            <div className="flex items-center justify-between gap-3 border-b border-white/10 pb-4">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-yellow-400/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
              </div>
              <span className="font-mono text-xs" style={{ color: "var(--color-text-secondary)" }}>devforge/run-suite.ts</span>
            </div>
            <div className="mt-5 space-y-3 font-mono text-xs leading-relaxed">
              <p><span style={{ color: "#A3A3A3" }}>const</span> tools = <span style={{ color: "#F5F5F5" }}>["Webhook Monitor", "FeedbackLens", "PriceTrackr"]</span>;</p>
              <p><span style={{ color: "#A3A3A3" }}>await</span> DevForge.cleanUp(<span style={{ color: "#F59E0B" }}>"messy_ops"</span>);</p>
              <div className="rounded-md bg-black/40 p-3">
                {[
                  ["Webhook Monitor", "3 failed events replayed"],
                  ["PriceTrackr", "7 drops detected"],
                  ["FeedbackLens", "12 new entries clustered"],
                ].map(([name, value]) => (
                  <div key={name} className="suite-console-row flex items-center justify-between gap-4 py-2">
                    <span style={{ color: "var(--color-text)" }}>{name}</span>
                    <span style={{ color: "var(--color-text-secondary)" }}>{value}</span>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-3 gap-2 pt-2">
                <div className="rounded-md border border-white/10 bg-black/30 p-3">
                  <p style={{ color: "var(--color-text-secondary)" }}>Live</p>
                  <p className="mt-1 text-lg font-bold" style={{ color: "var(--color-text)" }}>{liveCount}</p>
                </div>
                <div className="rounded-md border border-white/10 bg-black/30 p-3">
                  <p style={{ color: "var(--color-text-secondary)" }}>Plans</p>
                  <p className="mt-1 text-lg font-bold" style={{ color: "var(--color-text)" }}>3</p>
                </div>
                <div className="rounded-md border border-white/10 bg-black/30 p-3">
                  <p style={{ color: "var(--color-text-secondary)" }}>Demos</p>
                  <p className="mt-1 text-lg font-bold" style={{ color: "var(--color-text)" }}>4</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="products" className="py-16 md:py-20" style={{ backgroundColor: "var(--color-surface)" }}>
        <ProductGrid
          products={productCards}
          title="Four focused tools, four annoying chores"
          subtitle="Each product has a public demo, production dashboard paths, plan-aware limits, and copy that names the actual mess it handles."
        />
      </section>

      <section className="py-16 md:py-20">
        <div className="section-container grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
          <div>
            <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>Suite logic</p>
            <h2 className="heading-section mt-3 text-3xl md:text-4xl">Why these four tools belong together</h2>
            <div className="mt-4 space-y-3 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
              {DEVFORGE_SUITE.benefits.map((benefit) => (
                <p key={benefit}>{benefit}</p>
              ))}
            </div>
          </div>
          <div className="surface-card-raised border border-white/10 p-5">
            <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Operational chain</p>
            <div className="mt-5 grid gap-3">
              {[
                ["Broken integration", "Replay a failed webhook with evidence"],
                ["Market change", "Notice price drops before margins move"],
                ["Customer noise", "Cluster feedback with raw receipts"],
                ["Unpaid invoice", "Send reminders with human brakes"],
              ].map(([pain, detail]) => (
                <div key={pain} className="flex items-start gap-3 rounded-md bg-black/30 p-3">
                  <span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: "var(--color-accent)" }} />
                  <div>
                    <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>{pain}</p>
                    <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="plans" className="py-16 md:py-20">
        <div className="section-container">
          <div className="mb-8 max-w-3xl">
            <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Plans</p>
            <h2 className="heading-section mt-3 text-3xl md:text-4xl">One pricing shape across every product</h2>
            <p className="mt-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
              Each product keeps its own limits, but the upgrade logic stays predictable: Free to test, Pro to operate, Team to collaborate.
            </p>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            {suitePlans.map((plan) => (
              <div key={plan.name} className={`surface-card-raised flex flex-col border p-5 transition ${plan.name === "Pro" ? "relative -translate-y-2 border-[color:var(--color-accent)] shadow-[0_22px_50px_rgba(130,19,70,0.18)]" : "border-white/10"}`}>
                {plan.name === "Pro" ? (
                  <div className="mb-4 w-fit rounded-md border px-2.5 py-1 text-[0.68rem] font-bold uppercase tracking-normal" style={{ color: "var(--color-accent)", borderColor: "color-mix(in srgb, var(--color-accent) 48%, transparent)", backgroundColor: "var(--color-accent-dim)" }}>
                    Most popular
                  </div>
                ) : null}
                <StatusBadge tone={plan.name === "Pro" ? "accent" : plan.name === "Team" ? "success" : "neutral"} className="w-fit">{plan.name}</StatusBadge>
                <h3 className="mt-5 text-4xl font-bold tracking-normal" style={{ color: "var(--color-text)" }}>{plan.price}</h3>
                <p className="mt-3 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{plan.description}</p>
                <ul className="mt-5 flex-1 space-y-2">
                  {plan.limits.map((limit) => (
                    <li key={limit} className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{limit}</li>
                  ))}
                </ul>
                <a href={plan.name === "Free" ? "/register?plan=free" : plan.name === "Pro" ? "/register?plan=pro" : "/register?plan=team"} className={`mt-6 w-full ${plan.name === "Pro" ? "btn-primary" : "btn-outline"}`}>
                  {plan.name === "Free" ? "Start Free Now" : plan.name === "Pro" ? "Upgrade to Pro" : "Deploy Team"}
                </a>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="comparison" className="py-16 md:py-20" style={{ backgroundColor: "var(--color-surface)" }}>
        <div className="section-container">
          <div className="mb-8 max-w-3xl">
            <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Product comparison</p>
            <h2 className="heading-section mt-3 text-3xl">Pick the workflow you need first</h2>
            <p className="mt-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
              The suite is intentionally split into narrow tools, so you can start with the product that maps to your immediate pain.
            </p>
          </div>
          <div className="overflow-hidden rounded-md border border-white/10">
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead style={{ backgroundColor: "rgba(255,255,255,0.04)" }}>
                  <tr>
                    {["Product", "Status", "Best for", ...suiteComparison.map((item) => item.label), "Pro price"].map((heading) => (
                      <th key={heading} className="px-4 py-3 text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  {DEVFORGE_PRODUCTS.map((product) => {
                    const proPlan = product.plans.find((plan) => plan.slug === "pro");
                    return (
                      <tr key={product.slug} className="bg-black/20">
                        <td className="px-4 py-3 font-medium" style={{ color: "var(--color-text)" }}>
                          <a href={`#product-${product.slug}`} className="suite-product-link">
                            {product.name}
                          </a>
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge tone={product.status === "live" ? "success" : "neutral"}>
                            {product.status === "live" ? "Live" : "Beta pilot"}
                          </StatusBadge>
                        </td>
                        <td className="px-4 py-3" style={{ color: "var(--color-text-secondary)" }}>
                          {audienceTagsByProduct[product.slug].join(" / ")}
                        </td>
                        {suiteComparison.map((item) => (
                          <td key={item.key} className="px-4 py-3">
                            <AvailabilityIcon enabled={item.key !== "team" || product.status === "live"} />
                          </td>
                        ))}
                        <td className="px-4 py-3 font-mono" style={{ color: "var(--color-text)" }}>
                          {proPlan?.priceLabel || "$9.99"}/mo
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="py-16 md:py-20">
        <div className="section-container">
          <div className="closing-cta border border-white/10 p-8 text-center md:p-10">
            <h2 className="heading-section text-3xl md:text-4xl">Ready to clean up the ugly work?</h2>
            <p className="mx-auto mt-4 max-w-2xl leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
              Start free, test the live demos, and upgrade only when a workflow earns its keep.
            </p>
            <a href="/register?plan=free" className="btn-primary mt-8 px-8 py-4 text-base">
              Start Free Now
            </a>
          </div>
        </div>
      </section>
    </Layout>
  );
}
