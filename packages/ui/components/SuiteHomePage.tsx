import { DEVFORGE_PRODUCTS, DEVFORGE_SUITE } from "@devforge/core";
import type { ProductInfo } from "./ProductCard";
import { Layout } from "./Layout";
import { ProductGrid } from "./ProductGrid";
import { StatusBadge } from "./StatusBadge";

const audienceTagsByProduct = {
  filecleaner: ["Data teams", "Agencies", "Operators"],
  webhookmonitor: ["Developers", "API teams", "SaaS"],
  feedbacklens: ["Product teams", "Support", "Founders"],
  pricetrackr: ["Ecommerce", "Agencies", "Researchers"],
  invoicefollow: ["Freelancers", "Agencies", "Consultants"],
};

const productCards: ProductInfo[] = DEVFORGE_PRODUCTS.map((product) => ({
  slug: product.slug,
  name: product.name,
  tagline: product.headline,
  domain: product.domain,
  accentColor: product.accentColor,
  price: product.plans.find((plan) => plan.slug === "pro")?.price || 9.99,
  status: product.status,
  problem: product.problem,
  solution: product.solution,
  audienceTags: audienceTagsByProduct[product.slug],
}));

const suitePlans = [
  {
    name: "Free",
    price: "$0",
    description: "Try every product with practical limits before picking a paid workflow.",
    limits: ["Free limits per product", "Public demos", "Single-user workspace"],
  },
  {
    name: "Pro",
    price: "$9.99",
    description: "One product, higher limits, advanced workflow features, and production retention.",
    limits: ["Per product", "Advanced features", "Best for founders and solo operators"],
  },
  {
    name: "Team",
    price: "$49",
    description: "Higher limits, team seats where supported, longer retention, and deeper integrations.",
    limits: ["Per product", "Team limits", "Best for agencies and small teams"],
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
  const betaCount = DEVFORGE_PRODUCTS.filter((product) => product.status === "beta").length;

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
              <StatusBadge tone="success">{liveCount} live products</StatusBadge>
              <StatusBadge tone="neutral">{betaCount} beta pilots</StatusBadge>
              <StatusBadge tone="neutral">Free, Pro, Team</StatusBadge>
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
              <a href="#products" className="btn-ghost">Explore products</a>
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
              <p><span style={{ color: "#A3A3A3" }}>const</span> tools = <span style={{ color: "#F5F5F5" }}>["FileCleaner", "Webhook Monitor", "FeedbackLens"]</span>;</p>
              <p><span style={{ color: "#A3A3A3" }}>await</span> DevForge.automate(<span style={{ color: "#F59E0B" }}>"boring_ops"</span>);</p>
              <div className="rounded-md bg-black/40 p-3">
                {[
                  ["FileCleaner", "1,804 fixes queued"],
                  ["Webhook Monitor", "3 failed events replayed"],
                  ["PriceTrackr", "7 drops detected"],
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
                  <p className="mt-1 text-lg font-bold" style={{ color: "var(--color-text)" }}>5</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="products" className="py-16 md:py-20" style={{ backgroundColor: "var(--color-surface)" }}>
        <ProductGrid
          products={productCards}
          title="The five-product suite"
          subtitle="Each product has a public page, a safe interactive demo, a real dashboard, and Free/Pro/Team limits."
        />
      </section>

      <section id="plans" className="py-16 md:py-20">
        <div className="section-container">
          <div className="mb-8 max-w-3xl">
            <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Plans</p>
            <h2 className="heading-section mt-3 text-3xl md:text-4xl">Pricing stays predictable across products</h2>
            <p className="mt-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
              Every product starts at Free. Most Pro plans are $9.99/month and most Team plans are $49/month; FeedbackLens uses higher product-intelligence limits at $19/month Pro and $79/month Team.
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
            <h2 className="heading-section text-3xl md:text-4xl">Ready to automate the boring parts?</h2>
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
