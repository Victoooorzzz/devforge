import type { Metadata } from "next";
import { Layout } from "@devforge/ui";
import { HireFlipCard } from "./HireFlipCard";

const linkedInUrl = "https://www.linkedin.com/in/victor-villalobos-7a46b1317";

export const metadata: Metadata = {
  title: "Hire DevForge | Custom Websites and Web Apps",
  description:
    "Hire the developer behind DevForge to build custom websites, landing pages, product pages, dashboards, and production-ready web apps.",
  alternates: {
    canonical: "https://devforgeapp.pro/hire",
  },
};

const services = [
  {
    title: "Custom websites",
    body: "Modern marketing sites, personal brands, portfolios, and business pages built to look sharp and load fast.",
  },
  {
    title: "Landing pages",
    body: "Clear positioning, responsive design, conversion-focused sections, and production-ready deployment.",
  },
  {
    title: "Web apps",
    body: "Next.js interfaces, dashboards, backend integrations, auth, payments, and the product polish behind DevForge.",
  },
];

const products = ["File Cleaner", "Invoice Follow-up", "Price Tracker", "Webhook Monitor", "Feedback Lens"];

export default function HirePage() {
  return (
    <Layout
      productName="DevForge"
      productDomain="devforgeapp.pro"
      logoSrc="/devforge-logo-white.svg"
      navLinks={[
        { label: "Products", href: "/#products" },
        { label: "Hire", href: "/hire" },
      ]}
      ctaText="Start a build"
      ctaHref={linkedInUrl}
    >
      <section className="relative overflow-hidden">
        <div
          className="absolute left-1/2 top-0 h-[620px] w-[900px] -translate-x-1/2 rounded-full opacity-20 blur-3xl"
          style={{ background: "radial-gradient(ellipse, var(--color-accent) 0%, transparent 70%)" }}
        />
        <div className="section-container relative z-10 grid gap-12 py-20 md:grid-cols-[0.85fr_1.15fr] md:items-center md:py-28">
          <div>
            <p className="font-mono mb-5 text-xs" style={{ color: "var(--color-accent)" }}>
              HIRE THE DEVFORGE DEVELOPER
            </p>
            <h1 className="heading-display text-4xl leading-tight md:text-6xl">
              Custom websites built by the developer behind DevForge.
            </h1>
            <p
              className="mt-7 max-w-xl text-lg leading-relaxed"
              style={{ color: "var(--color-text-secondary)" }}
            >
              I create custom web pages, landing pages, and full web experiences for people who
              want a clean technical build without bloated agency process.
            </p>
            <div className="mt-9 flex flex-col gap-4 sm:flex-row">
              <a
                href={linkedInUrl}
                target="_blank"
                rel="noreferrer"
                className="btn-primary px-8 py-3 text-base"
              >
                Start a build
              </a>
              <a href="/#products" className="btn-secondary px-8 py-3 text-base">
                See DevForge products
              </a>
            </div>
          </div>

          <div className="w-full max-w-[430px] justify-self-center md:justify-self-end">
            <HireFlipCard />
          </div>
        </div>
      </section>

      <section className="py-16 md:py-24" style={{ backgroundColor: "var(--color-surface)" }}>
        <div className="section-container grid gap-10 md:grid-cols-[0.8fr_1.2fr]">
          <div>
            <p className="font-mono mb-4 text-xs" style={{ color: "var(--color-accent)" }}>
              WHAT I BUILD
            </p>
            <h2 className="heading-section text-3xl md:text-4xl">Websites that feel custom, not templated.</h2>
          </div>
          <div className="grid gap-4">
            {services.map((service) => (
              <div
                key={service.title}
                className="rounded-[4px] p-6"
                style={{ backgroundColor: "var(--color-bg)" }}
              >
                <h3 className="heading-section text-xl">{service.title}</h3>
                <p className="mt-3 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                  {service.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 md:py-24">
        <div className="section-container">
          <div className="grid gap-8 md:grid-cols-[1fr_1.15fr] md:items-end">
            <div>
              <p className="font-mono mb-4 text-xs" style={{ color: "var(--color-accent)" }}>
                PROOF OF WORK
              </p>
              <h2 className="heading-section text-3xl md:text-4xl">DevForge is the portfolio.</h2>
            </div>
            <p className="leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
              This site is part of a monorepo with five shipped products. That means your website
              can be designed, built, deployed, and extended with the same production habits.
            </p>
          </div>

          <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {products.map((product) => (
              <div
                key={product}
                className="rounded-[4px] px-4 py-5"
                style={{ backgroundColor: "var(--color-surface)" }}
              >
                <p className="font-mono text-xs" style={{ color: "var(--color-accent)" }}>
                  DEVFORGE
                </p>
                <p className="mt-2 font-semibold" style={{ color: "var(--color-text)" }}>
                  {product}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 md:py-24" style={{ backgroundColor: "var(--color-surface)" }}>
        <div className="section-container text-center">
          <h2 className="heading-section text-3xl md:text-4xl">Need a custom website?</h2>
          <p
            className="mx-auto mt-5 max-w-2xl text-lg leading-relaxed"
            style={{ color: "var(--color-text-secondary)" }}
          >
            Tell me what you need, what you sell, and what you want the page to do. I will turn it
            into a sharp, responsive website with DevForge-level execution.
          </p>
          <a
            href={linkedInUrl}
            target="_blank"
            rel="noreferrer"
            className="btn-primary mt-9 px-8 py-3 text-base"
          >
            Contact DevForge
          </a>
        </div>
      </section>
    </Layout>
  );
}
