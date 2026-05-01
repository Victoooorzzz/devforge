"use client";
import Link from "next/link";
import { Check, Zap, Target, TrendingDown } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-accent selection:text-black">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 glass border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <img src="/devforge-logo-white.svg" alt="DevForge" className="h-6 w-auto" />
            <span className="text-xl font-bold tracking-tighter border-l border-white/20 pl-3">
              Price<span className="text-accent">Trackr</span>
            </span>
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-neutral-400">
            <Link href="#features" className="hover:text-white transition-colors">Features</Link>
            <Link href="#pricing" className="hover:text-white transition-colors">Pricing</Link>
            <Link href="/login" className="hover:text-white transition-colors">Login</Link>
            <Link href="/register" className="btn-primary px-5 py-2">Get Started</Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6 min-h-[85vh] flex flex-col justify-center">
        <div className="max-w-6xl mx-auto w-full grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 text-accent text-xs font-medium mb-6">
              <Target size={14} />
              <span>Real-time Market Intelligence</span>
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-b from-white to-white/50 bg-clip-text text-transparent">
              Outsmart your competitors.
            </h1>
            <p className="text-lg md:text-xl text-neutral-400 mb-10">
              Monitor competitor prices in real-time, get instant alerts on price drops, and optimize your margins with data-driven insights.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link href="/register" className="btn-primary px-8 py-4 text-center">
                Start Tracking
              </Link>
            </div>
          </div>
          
          {/* Chart UI */}
          <div className="relative w-full h-[400px] rounded-lg overflow-hidden bg-[#0A0A0A] border border-[#282627] shadow-2xl p-6 flex flex-col justify-end">
            {/* Header / Badges */}
            <div className="absolute top-6 left-6 right-6 flex justify-between items-center z-10">
              <div className="text-white font-mono text-sm">
                COMPETITOR: <span className="text-neutral-400">MARKET_LEADER_US</span>
              </div>
              <div className="flex items-center gap-2 bg-accent/20 text-accent px-3 py-1 rounded-full text-xs font-bold border border-accent/30 animate-pulse">
                <span className="w-2 h-2 rounded-full bg-accent"></span>
                PRICE DROP DETECTED
              </div>
            </div>

            {/* Price tag */}
            <div className="absolute top-20 left-6 z-10">
              <div className="text-5xl font-bold tracking-tighter text-white font-mono">
                $899<span className="text-xl text-neutral-500">.99</span>
              </div>
              <div className="text-sm font-mono text-accent mt-2 flex items-center gap-1">
                <TrendingDown size={14} /> -12.5% in last 10m
              </div>
            </div>
            
            {/* Minimalist SVG Graph */}
            <div className="absolute inset-0 pt-[150px] flex items-end">
              <svg viewBox="0 0 100 50" className="w-full h-full preserve-3d" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="gradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#821346" stopOpacity="0.5" />
                    <stop offset="100%" stopColor="#821346" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <path d="M0 40 Q 10 30, 20 35 T 40 20 T 60 25 T 80 15 T 100 5 L 100 50 L 0 50 Z" fill="url(#gradient)" />
                <path d="M0 40 Q 10 30, 20 35 T 40 20 T 60 25 T 80 15 T 100 5" fill="none" stroke="#821346" strokeWidth="0.5" className="drop-shadow-[0_0_8px_#821346]" />
                
                {/* Active Point Indicator */}
                <circle cx="100" cy="5" r="1.5" fill="#821346" className="animate-ping" />
                <circle cx="100" cy="5" r="1" fill="#fff" />
              </svg>
            </div>
            
            {/* Grid overlay */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff05_1px,transparent_1px),linear-gradient(to_bottom,#ffffff05_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none mix-blend-overlay"></div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-6 border-t border-white/5">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="glass p-8 rounded-2xl border border-white/5">
              <TrendingDown className="text-accent mb-4" size={32} />
              <h3 className="text-xl font-bold mb-3">Price Monitoring</h3>
              <p className="text-neutral-400 text-sm leading-relaxed">
                Track prices across thousands of websites and marketplaces with 10-minute refresh intervals.
              </p>
            </div>
            <div className="glass p-8 rounded-2xl border border-white/5">
              <Zap className="text-accent mb-4" size={32} />
              <h3 className="text-xl font-bold mb-3">Instant Alerts</h3>
              <p className="text-neutral-400 text-sm leading-relaxed">
                Receive instant notifications via Telegram, Discord, or Email when a competitor changes their pricing.
              </p>
            </div>
            <div className="glass p-8 rounded-2xl border border-white/5">
              <Check className="text-accent mb-4" size={32} />
              <h3 className="text-xl font-bold mb-3">Historical Data</h3>
              <p className="text-neutral-400 text-sm leading-relaxed">
                Analyze pricing trends over time to identify seasonal patterns and competitor strategies.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 px-6 border-t border-white/5 bg-white/[0.02]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Pricing for elite ecommerce teams.</h2>
            <p className="text-neutral-400">Maximize your market share with professional tracking tools.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Starter */}
            <div className="glass p-10 rounded-3xl border border-white/10 flex flex-col">
              <div className="mb-8">
                <h3 className="text-xl font-bold mb-2">Starter</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-bold">$9.99</span>
                  <span className="text-neutral-400">/mo</span>
                </div>
                <p className="text-sm text-neutral-400 mt-4">For solo sellers and boutique stores.</p>
              </div>
              <ul className="space-y-4 mb-10 flex-1">
                {["100 Tracked URLs", "1-Hour Refresh Rate", "Email Alerts", "30-Day History", "Single User"].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-sm text-neutral-300">
                    <Check size={16} className="text-accent" /> {item}
                  </li>
                ))}
              </ul>
              <Link href="/register?plan=starter" className="btn-primary py-4 text-center">
                Start 7-Day Free Trial
              </Link>
            </div>

            {/* Pro */}
            <div className="glass p-10 rounded-3xl border-2 border-accent/50 relative flex flex-col overflow-hidden">
              <div className="absolute top-0 right-0 bg-accent text-black text-[10px] font-bold px-3 py-1 uppercase tracking-widest rounded-bl-xl">
                Best ROI
              </div>
              <div className="mb-8">
                <h3 className="text-xl font-bold mb-2">Pro</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-bold">$9.99</span>
                  <span className="text-neutral-400">/mo</span>
                </div>
                <p className="text-sm text-neutral-400 mt-4">Enterprise-grade tracking for large retailers.</p>
              </div>
              <ul className="space-y-4 mb-10 flex-1">
                {["10,000 Tracked URLs", "10-Minute Refresh Rate", "Webhook & Slack Alerts", "Lifetime History", "Unlimited Team Members", "Priority Proxy Network"].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-sm text-neutral-300">
                    <Check size={16} className="text-accent" /> {item}
                  </li>
                ))}
              </ul>
              <Link href="/register?plan=pro" className="btn-primary py-4 text-center">
                Get Started with Pro
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-white/5 text-center text-neutral-500 text-sm">
        <p>&copy; 2024 PriceTrackr. Part of the DevForge ecosystem.</p>
      </footer>
    </div>
  );
}
