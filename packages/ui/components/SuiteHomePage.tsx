import { DEVFORGE_PRODUCTS, DEVFORGE_SUITE } from "@devforge/core";
import Image from "next/image";
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
              <StatusBadge tone="accent">Free, Pro, Team</StatusBadge>
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
          <div className="surface-card-raised border border-white/10 p-5 animate-scale-in">
            <Image src="/devforge-logo-white.svg" alt="DevForge" width={144} height={32} className="h-8 w-auto" style={{ width: "auto", height: "auto" }} priority />
            <div className="mt-6 grid gap-3">
              {DEVFORGE_SUITE.benefits.map((benefit) => (
                <div key={benefit} className="rounded-md bg-black/30 p-4 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                  {benefit}
                </div>
              ))}
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
            <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>Plans</p>
            <h2 className="heading-section mt-3 text-3xl md:text-4xl">Pricing stays predictable across products</h2>
            <p className="mt-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
              Every product starts at Free. Most Pro plans are $9.99/month and most Team plans are $49/month; FeedbackLens uses higher product-intelligence limits at $19/month Pro and $79/month Team.
            </p>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            {suitePlans.map((plan) => (
              <div key={plan.name} className={`surface-card-raised border p-5 ${plan.name === "Pro" ? "border-[color:var(--color-accent)]" : "border-white/10"}`}>
                <StatusBadge tone={plan.name === "Pro" ? "accent" : plan.name === "Team" ? "success" : "neutral"}>{plan.name}</StatusBadge>
                <h3 className="mt-5 text-4xl font-bold tracking-normal" style={{ color: "var(--color-text)" }}>{plan.price}</h3>
                <p className="mt-3 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{plan.description}</p>
                <ul className="mt-5 space-y-2">
                  {plan.limits.map((limit) => (
                    <li key={limit} className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{limit}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="comparison" className="py-16 md:py-20" style={{ backgroundColor: "var(--color-surface)" }}>
        <div className="section-container">
          <div className="mb-8 max-w-3xl">
            <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>Product comparison</p>
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
                    {["Product", "Status", "Best for", "Pro price", "Primary job"].map((heading) => (
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
                          {product.name}
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge tone={product.status === "live" ? "success" : "neutral"}>
                            {product.status === "live" ? "Live" : "Beta pilot"}
                          </StatusBadge>
                        </td>
                        <td className="px-4 py-3" style={{ color: "var(--color-text-secondary)" }}>
                          {audienceTagsByProduct[product.slug].join(" / ")}
                        </td>
                        <td className="px-4 py-3 font-mono" style={{ color: "var(--color-text)" }}>
                          {proPlan?.priceLabel || "$9.99"}/mo
                        </td>
                        <td className="px-4 py-3" style={{ color: "var(--color-text-secondary)" }}>
                          {product.useCases[0]}
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
    </Layout>
  );
}
