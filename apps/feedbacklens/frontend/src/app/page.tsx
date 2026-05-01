"use client";
import Link from "next/link";

const FEATURES = [
  { icon: "🧠", title: "AI Sentiment Analysis", desc: "Detect positive, negative, and neutral sentiment in seconds with confidence scores." },
  { icon: "🏷️", title: "Theme Extraction", desc: "Automatically group feedback into recurring themes so you spot patterns fast." },
  { icon: "📊", title: "Real-time Dashboard", desc: "See all your feedback in one place with live stats and instant analysis." },
  { icon: "🔌", title: "API Ready", desc: "Push feedback from your app directly via our REST API. No manual work." },
];

const PLANS = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Perfect to get started",
    features: ["50 feedback analyses/month", "Sentiment detection", "Basic themes", "Dashboard access"],
    cta: "Start Free",
    href: "/register",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$19",
    period: "per month",
    description: "For growing products",
    features: ["Unlimited analyses", "Advanced theme clustering", "Priority AI processing", "API access", "CSV export", "Email support"],
    cta: "Start 7-day Trial",
    href: "/register?plan=pro",
    highlighted: true,
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen" style={{ backgroundColor: "var(--color-bg)" }}>
      {/* Nav */}
      <nav className="glass border-b sticky top-0 z-50" style={{ borderColor: "var(--color-border)" }}>
        <div className="section-container flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold" style={{ color: "var(--color-accent)" }}>FeedbackLens</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login" className="btn-ghost text-sm">Sign in</Link>
            <Link href="/register" className="btn-primary text-sm">Start Free</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="section-container pt-24 pb-20 text-center">
        <div className="badge mb-6">AI-Powered · No credit card required</div>
        <h1 className="heading-display text-5xl mb-6 max-w-3xl mx-auto text-balance">
          Understand what your users <span style={{ color: "var(--color-accent)" }}>really think</span>
        </h1>
        <p className="text-lg mb-10 max-w-xl mx-auto" style={{ color: "var(--color-text-secondary)" }}>
          Paste feedback, get instant AI sentiment analysis and theme extraction. Stop reading every review manually.
        </p>
        <div className="flex items-center justify-center gap-4 flex-wrap">
          <Link href="/register" className="btn-primary px-8 py-3 text-base">Start for Free</Link>
          <Link href="/login" className="btn-secondary px-8 py-3 text-base">Sign in</Link>
        </div>
        <p className="text-xs mt-4" style={{ color: "var(--color-text-secondary)" }}>
          50 free analyses per month · No credit card required
        </p>
      </section>

      {/* Features */}
      <section className="section-container pb-20">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {FEATURES.map((f) => (
            <div key={f.title} className="surface-card-raised p-6">
              <div className="text-3xl mb-4">{f.icon}</div>
              <h3 className="font-semibold mb-2" style={{ color: "var(--color-text)" }}>{f.title}</h3>
              <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section className="section-container pb-24">
        <h2 className="heading-section text-3xl text-center mb-3">Simple pricing</h2>
        <p className="text-center mb-12" style={{ color: "var(--color-text-secondary)" }}>
          Start free. Upgrade when you need more.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-2xl mx-auto">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className="surface-card p-8 flex flex-col"
              style={plan.highlighted ? { border: `1px solid var(--color-accent)`, borderRadius: "var(--radius-lg)" } : { border: "1px solid var(--color-border)", borderRadius: "var(--radius-lg)" }}
            >
              {plan.highlighted && (
                <div className="badge mb-4 self-start">Most popular</div>
              )}
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-1" style={{ color: "var(--color-text)" }}>{plan.name}</h3>
                <p className="text-sm mb-4" style={{ color: "var(--color-text-secondary)" }}>{plan.description}</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-bold" style={{ color: "var(--color-text)" }}>{plan.price}</span>
                  <span className="text-sm" style={{ color: "var(--color-text-secondary)" }}>/{plan.period}</span>
                </div>
              </div>
              <ul className="space-y-3 mb-8 flex-1">
                {plan.features.map((feat) => (
                  <li key={feat} className="flex items-center gap-2 text-sm" style={{ color: "var(--color-text-secondary)" }}>
                    <span style={{ color: "var(--color-accent)" }}>✓</span> {feat}
                  </li>
                ))}
              </ul>
              <Link href={plan.href} className={plan.highlighted ? "btn-primary text-center" : "btn-secondary text-center"}>
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8" style={{ borderColor: "var(--color-border)" }}>
        <div className="section-container flex items-center justify-between text-sm" style={{ color: "var(--color-text-secondary)" }}>
          <span>© 2025 FeedbackLens · Part of <a href="https://devforgeapp.pro" className="underline">DevForge</a></span>
          <div className="flex gap-6">
            <Link href="/login">Sign in</Link>
            <Link href="/register">Register</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
