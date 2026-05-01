"use client";
import Link from "next/link";

import { MessageSquare, ThumbsUp, ThumbsDown, Minus, Zap } from "lucide-react";

const FEATURES = [
  { icon: "🧠", title: "AI Sentiment Analysis", desc: "Detect positive, negative, and neutral sentiment in seconds with confidence scores." },
  { icon: "🏷️", title: "Theme Extraction", desc: "Automatically group feedback into recurring themes so you spot patterns fast." },
  { icon: "📊", title: "Real-time Dashboard", desc: "See all your feedback in one place with live stats and instant analysis." },
  { icon: "🔌", title: "API Ready", desc: "Push feedback from your app directly via our REST API. No manual work." },
];

const PLANS = [
  {
    name: "Starter",
    price: "$9.99",
    period: "per month",
    description: "Perfect to get started",
    features: ["500 feedback analyses/month", "Sentiment detection", "Basic themes", "Dashboard access", "Email support"],
    cta: "Start 7-day Trial",
    href: "/register?plan=starter",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$9.99",
    period: "per month",
    description: "For growing products",
    features: ["Unlimited analyses", "Advanced theme clustering", "Priority AI processing", "API access", "CSV export", "Priority support"],
    cta: "Get Started with Pro",
    href: "/register?plan=pro",
    highlighted: true,
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-[#821346] selection:text-white font-sans">
      {/* Nav */}
      <nav className="glass border-b border-white/5 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <img src="/devforge-logo-white.svg" alt="DevForge" className="h-6 w-auto" />
            <span className="text-xl font-bold tracking-tighter border-l border-white/20 pl-3">
              Feedback<span className="text-[#821346]">Lens</span>
            </span>
          </Link>
          <div className="flex items-center gap-4 text-sm font-medium">
            <Link href="/login" className="text-neutral-400 hover:text-white transition-colors">Sign in</Link>
            <Link href="/register" className="bg-[#821346] text-white px-5 py-2 hover:bg-[#821346]/90 transition-colors uppercase tracking-wider text-xs font-bold rounded-sm">
              Start Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6 min-h-[85vh] flex flex-col justify-center overflow-hidden">
        <div className="max-w-6xl mx-auto w-full grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="text-left relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-sm bg-[#821346]/10 border border-[#821346]/20 text-[#821346] text-xs font-bold mb-6 uppercase tracking-widest">
              <Zap size={14} />
              <span>AI-Powered Sentiment Analysis</span>
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-b from-white to-white/50 bg-clip-text text-transparent">
              Understand what users really think.
            </h1>
            <p className="text-lg md:text-xl text-neutral-400 mb-10">
              Paste feedback, get instant AI sentiment analysis and theme extraction. Stop reading every review manually and start making data-driven product decisions.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link href="/register" className="bg-[#821346] text-white px-8 py-4 text-center hover:bg-[#821346]/90 transition-colors uppercase tracking-wider text-sm font-bold rounded-sm">
                Analyze Feedback Now
              </Link>
            </div>
          </div>
          
          {/* Sentiment Cards UI */}
          <div className="relative w-full h-[450px] flex items-center justify-center">
            {/* Background decorative elements */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(130,19,70,0.1)_0,transparent_70%)]"></div>
            
            <div className="relative w-full max-w-md">
              {/* Positive Card */}
              <div className="absolute top-0 right-0 transform translate-x-4 -translate-y-16 w-64 bg-[#0A0A0A] border border-[#282627] rounded-lg p-4 shadow-2xl z-30 animate-[float_6s_ease-in-out_infinite]">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center">
                      <ThumbsUp size={12} className="text-green-500" />
                    </div>
                    <span className="text-xs font-bold text-white tracking-widest uppercase">Positive</span>
                  </div>
                  <span className="text-[10px] font-mono text-green-500">98% Match</span>
                </div>
                <p className="text-xs text-neutral-400 italic">"The new drag and drop feature saves me hours every week. Absolutely brilliant update."</p>
                <div className="mt-3 flex gap-2">
                  <span className="text-[9px] px-2 py-0.5 rounded-sm bg-white/5 text-neutral-300 font-mono">#UX</span>
                  <span className="text-[9px] px-2 py-0.5 rounded-sm bg-white/5 text-neutral-300 font-mono">#Productivity</span>
                </div>
              </div>

              {/* Negative Card */}
              <div className="absolute bottom-0 left-0 transform -translate-x-8 translate-y-16 w-64 bg-[#0A0A0A] border border-[#282627] rounded-lg p-4 shadow-2xl z-20 animate-[float_7s_ease-in-out_infinite_reverse]">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-red-500/20 flex items-center justify-center">
                      <ThumbsDown size={12} className="text-red-500" />
                    </div>
                    <span className="text-xs font-bold text-white tracking-widest uppercase">Negative</span>
                  </div>
                  <span className="text-[10px] font-mono text-red-500">92% Match</span>
                </div>
                <p className="text-xs text-neutral-400 italic">"The app keeps crashing when I try to export large PDF files. Please fix this."</p>
                <div className="mt-3 flex gap-2">
                  <span className="text-[9px] px-2 py-0.5 rounded-sm bg-white/5 text-neutral-300 font-mono">#Bug</span>
                  <span className="text-[9px] px-2 py-0.5 rounded-sm bg-white/5 text-neutral-300 font-mono">#Export</span>
                </div>
              </div>

              {/* Central AI Processor Card */}
              <div className="relative bg-[#191718] border-2 border-[#821346]/50 rounded-lg p-6 shadow-[0_0_30px_rgba(130,19,70,0.2)] z-10 mx-auto w-72">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-black px-2">
                  <div className="px-3 py-1 rounded-sm bg-[#821346] text-white text-[10px] font-bold tracking-widest uppercase flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span>
                    Processing Engine
                  </div>
                </div>
                <div className="flex flex-col items-center text-center mt-2">
                  <div className="w-12 h-12 rounded-full border border-neutral-700 flex items-center justify-center mb-4 relative">
                    <MessageSquare size={20} className="text-neutral-400" />
                    <div className="absolute inset-0 border-2 border-transparent border-t-[#821346] rounded-full animate-spin"></div>
                  </div>
                  <div className="w-full bg-black h-1.5 rounded-full overflow-hidden mb-2">
                    <div className="bg-[#821346] h-full w-2/3 animate-[pulse_2s_ease-in-out_infinite]"></div>
                  </div>
                  <span className="text-[10px] font-mono text-neutral-500 uppercase">Analyzing 1,204 feedback items...</span>
                </div>
              </div>
            </div>
          </div>
        </div>
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
