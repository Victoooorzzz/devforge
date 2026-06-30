"use client";

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
                  {product.status === "live" ? "Live product" : "Beta product"}
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
                <Image src="/devforge-logo-white.svg" alt="DevForge" width={126} height={28} className="h-7 w-auto" />
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
                <IntegrationCard key={feature} name={feature} description={`Available in the ${product.shortName} workflow with plan-aware limits and dashboard state.`} status="Included" tone="accent" />
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

        <section className="py-16 md:py-20">
          <div className="section-container">
            <div className="mb-8 max-w-3xl">
              <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>DevForge suite</p>
              <h2 className="heading-section mt-3 text-3xl">Other tools in the same stack</h2>
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {relatedProducts.map((item) => (
                <a key={item.slug} href={item.url} className="surface-card-raised border border-white/10 p-4 transition hover:border-white/20">
                  <StatusBadge tone={item.status === "live" ? "success" : "accent"}>{item.status}</StatusBadge>
                  <h3 className="mt-4 text-lg font-semibold" style={{ color: "var(--color-text)" }}>{item.name}</h3>
                  <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{item.description}</p>
                </a>
              ))}
            </div>
          </div>
        </section>
      </Layout>
    </div>
  );
}
