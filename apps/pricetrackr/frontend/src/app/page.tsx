"use client";
import Link from "next/link";
import { Check, Zap, Target, TrendingDown, Search, Bell, BarChart2, Globe, ArrowUpRight, Activity } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-accent selection:text-black">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 glass border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <img src="/devforge-logo-white.svg" alt="DevForge" className="h-6 w-auto" />
            <span className="text-xl font-bold tracking-tighter border-l border-white/20 pl-3 uppercase">
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
      <section className="pt-32 pb-20 px-6 min-h-[90vh] flex flex-col items-center justify-center relative overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full bg-[radial-gradient(circle_at_center,rgba(130,19,70,0.08)_0,transparent_70%)] pointer-events-none"></div>
        
        <div className="max-w-6xl mx-auto w-full text-center relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 text-accent text-[10px] font-bold mb-8 uppercase tracking-widest">
            <Activity size={12} />
            <span>Market Surveillance Online</span>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-b from-white to-white/50 bg-clip-text text-transparent uppercase text-balance">
            Outsmart Competitors with Real-Time Data.
          </h1>
          <p className="text-lg md:text-xl text-neutral-400 max-w-2xl mx-auto mb-12">
            Monitor thousands of URLs with 10-minute refresh rates. 
            Detect price drops, stock changes, and market shifts before anyone else.
          </p>

          {/* PRICE CHART VISUAL */}
          <div className="max-w-4xl mx-auto mb-16 glass p-6 rounded-2xl border border-white/5 bg-black/40 relative overflow-hidden group">
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center border border-white/10">
                  <Globe size={20} className="text-neutral-400" />
                </div>
                <div className="text-left">
                  <p className="text-xs font-mono text-neutral-500 uppercase tracking-tighter">Target URL</p>
                  <p className="text-sm font-bold truncate max-w-[200px]">amazon.com/pro-laptop-2024</p>
                </div>
              </div>
              <div className="flex gap-2">
                <div className="px-3 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-[10px] font-bold uppercase tracking-widest">
                  Live: $1,249.00
                </div>
                <div className="px-3 py-1 rounded-md bg-accent/10 border border-accent/20 text-accent text-[10px] font-bold uppercase tracking-widest animate-pulse">
                  Drop Detected
                </div>
              </div>
            </div>

            <div className="h-48 relative">
              <svg viewBox="0 0 400 100" className="w-full h-full preserve-3d" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="priceGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#821346" stopOpacity="0.3" />
                    <stop offset="100%" stopColor="#821346" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <path d="M0 80 L 50 75 L 100 85 L 150 40 L 200 45 L 250 20 L 300 25 L 350 10 L 400 15 L 400 100 L 0 100 Z" fill="url(#priceGradient)" />
                <path d="M0 80 L 50 75 L 100 85 L 150 40 L 200 45 L 250 20 L 300 25 L 350 10 L 400 15" fill="none" stroke="#821346" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="150" cy="40" r="3" fill="#821346" />
                <circle cx="350" cy="10" r="4" fill="#821346" className="animate-ping" />
                <circle cx="350" cy="10" r="2" fill="#fff" />
              </svg>
              
              {/* Grid Lines */}
              <div className="absolute inset-0 border-b border-white/5 flex flex-col justify-between pointer-events-none">
                <div className="border-t border-white/5 w-full"></div>
                <div className="border-t border-white/5 w-full"></div>
                <div className="border-t border-white/5 w-full"></div>
              </div>
            </div>
            
            <div className="mt-4 flex justify-between text-[10px] font-mono text-neutral-500 uppercase">
              <span>08:00 AM</span>
              <span>12:00 PM</span>
              <span>04:00 PM</span>
              <span>08:00 PM</span>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/register" className="btn-primary px-10 py-4 text-lg">
              Start Surveillance Free
            </Link>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="py-24 px-6 bg-white/[0.01] border-y border-white/5">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-xs font-bold uppercase tracking-widest text-accent mb-4">Market Intelligence</h2>
            <h3 className="text-3xl md:text-5xl font-bold">Monitor in 3 simple steps.</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 text-center">
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <Search className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">1. Track URLs</h4>
              <p className="text-neutral-400 text-sm">Paste URLs from any marketplace. Our engine identifies price & stock selectors automatically.</p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <Bell className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">2. Detect Changes</h4>
              <p className="text-neutral-400 text-sm">We scan every 10 minutes. Get instant alerts via Webhook, Slack, or Email on any movement.</p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <BarChart2 className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">3. Beat Prices</h4>
              <p className="text-neutral-400 text-sm">Use historical data to optimize your own margins and stay #1 in the market.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 px-6 border-t border-white/5 bg-white/[0.02]">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Industrial-grade intelligence.</h2>
            <p className="text-neutral-400">Everything you need to dominate your e-commerce niche.</p>
          </div>

          <div className="max-w-lg mx-auto">
            <div className="glass p-10 rounded-3xl border-2 border-accent relative flex flex-col overflow-hidden shadow-[0_0_50px_rgba(130,19,70,0.2)]">
              <div className="absolute top-0 right-0 bg-accent text-black text-[10px] font-bold px-4 py-1.5 uppercase tracking-widest rounded-bl-xl">
                Pro Access
              </div>
              <div className="mb-8">
                <h3 className="text-2xl font-bold mb-2">Pro Plan</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-5xl font-bold">$9.99</span>
                  <span className="text-neutral-400">/mo</span>
                </div>
                <p className="text-sm text-neutral-400 mt-4 leading-relaxed">
                  Real-time tracking for up to 10,000 URLs. Includes a 7-day free trial.
                </p>
              </div>
              <ul className="space-y-4 mb-10">
                {[
                  "10,000 Tracked URLs",
                  "10-Minute Refresh Intervals",
                  "Global Proxy Network",
                  "Price History Tracking",
                  "Custom Webhook Alerts",
                  "Priority 24/7 Support"
                ].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-sm text-neutral-300">
                    <Check size={18} className="text-accent" /> {item}
                  </li>
                ))}
              </ul>
              <div className="flex flex-col gap-4">
                <Link href="/register" className="btn-primary py-4 text-center font-bold text-lg">
                  Start 7-Day Free Trial
                </Link>
                <p className="text-[10px] text-center text-neutral-500 uppercase tracking-widest">
                  Cancel anytime during trial • No hidden fees
                </p>
              </div>
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

