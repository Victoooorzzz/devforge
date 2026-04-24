// apps/template/frontend/src/app/page.tsx

import { Layout, LandingHero, FeatureGrid, PricingCard, Testimonials } from "@devforge/ui";
import { product } from "@/config/product";
import { PricingSection } from "./pricing-section";

const featureIcons = [
  <svg key="1" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>,
  <svg key="2" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>,
  <svg key="3" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/><path d="M9 12l2 2 4-4"/></svg>,
];

export default function HomePage() {
  const featuresWithIcons = product.features.map((f, i) => ({
    ...f,
    icon: featureIcons[i % featureIcons.length],
  }));

  return (
    <Layout
      productName={product.name}
      productDomain={product.domain}
      navLinks={product.navLinks}
    >
      <LandingHero
        badge={product.hero.badge}
        headline={product.hero.headline}
        subtitle={product.hero.subtitle}
        ctaText={product.hero.ctaText}
        ctaHref={product.hero.ctaHref}
        secondaryCtaText={product.hero.secondaryCtaText}
        secondaryCtaHref={product.hero.secondaryCtaHref}
      />

      <div id="features">
        <FeatureGrid
          title="Everything you need"
          subtitle="Built for speed, simplicity, and results"
          features={featuresWithIcons}
        />
      </div>

      <Testimonials testimonials={product.testimonials} />

      <div id="pricing">
        <PricingSection />
      </div>
    </Layout>
  );
}
