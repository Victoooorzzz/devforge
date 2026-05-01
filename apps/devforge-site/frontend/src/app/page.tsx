import { Layout, LandingHero, ProductGrid } from "@devforge/ui";
import type { ProductInfo } from "@devforge/ui";

const products: ProductInfo[] = [
  {
    name: "File Cleaner",
    tagline: "Industrial-grade processing for chaotic data payloads",
    domain: "filecleaner.devforgeapp.pro",
    accentColor: "#821346",
    price: 9.99,
    status: "live",
  },
  {
    name: "Invoice Follow-up",
    tagline: "Automated payment recovery for growing businesses",
    domain: "invoicefollow.devforgeapp.pro",
    accentColor: "#821346",
    price: 9.99,
    status: "live",
  },
  {
    name: "Price Tracker",
    tagline: "Real-time market intelligence and price monitoring",
    domain: "pricetrackr.devforgeapp.pro",
    accentColor: "#821346",
    price: 9.99,
    status: "live",
  },
  {
    name: "Webhook Monitor",
    tagline: "Terminal-grade webhook inspection and debugging",
    domain: "webhookmonitor.devforgeapp.pro",
    accentColor: "#821346",
    price: 9.99,
    status: "live",
  },
  {
    name: "Feedback Lens",
    tagline: "AI-powered sentiment analysis for customer feedback",
    domain: "feedbacklens.devforgeapp.pro",
    accentColor: "#821346",
    price: 9.99,
    status: "live",
  },
];

export default function HomePage() {
  return (
    <Layout 
      productName="DevForge" 
      productDomain="devforgeapp.pro" 
      logoSrc="/devforge-logo-white.svg"
      navLinks={[{ label: "Products", href: "#products" }]} 
      ctaText="Explore" 
      ctaHref="#products"
    >
      <LandingHero
        badge="5 Products. 1 Vision."
        headline="Indie SaaS Tools for Developers & Freelancers"
        subtitle="Micro-products that solve real problems. No bloat, no enterprise pricing. Just tools that work — built by one developer, used by thousands."
        ctaText="See Products"
        ctaHref="#products"
        secondaryCtaText="View Source"
        secondaryCtaHref="https://github.com/devforge"
      />

      <div id="products">
        <ProductGrid
          products={products}
          title="The Product Suite"
          subtitle="Each product is independent, focused, and priced for indie developers and small teams."
        />
      </div>

      {/* About Section */}
      <section className="py-20 md:py-28" style={{ backgroundColor: "var(--color-surface)" }}>
        <div className="section-container text-center max-w-2xl mx-auto">
          <h2 className="heading-section text-3xl md:text-4xl mb-6">Built Different</h2>
          <p className="text-lg leading-relaxed mb-4" style={{ color: "var(--color-text-secondary)" }}>
            DevForge is a collection of opinionated micro-SaaS products. Each tool does one thing exceptionally well —
            no feature creep, no enterprise lock-in. Every product shares the same design DNA, authentication system,
            and billing infrastructure.
          </p>
          <p className="text-lg leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
            Built with Next.js, FastAPI, and a shared monorepo architecture. Designed for developers who value
            simplicity, speed, and transparent pricing.
          </p>
          <div className="flex flex-wrap justify-center gap-8 mt-12">
            {[
              { value: "5", label: "Products" },
              { value: "$9.99", label: "/month" },
              { value: "100%", label: "Indie Built" },
            ].map((stat) => (
              <div key={stat.label}>
                <p className="text-3xl font-bold font-mono" style={{ color: "var(--color-accent)" }}>{stat.value}</p>
                <p className="text-sm mt-1" style={{ color: "var(--color-text-secondary)" }}>{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </Layout>
  );
}
