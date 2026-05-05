"use client";
import Link from "next/link";
import { Check, Zap, Clock, Bell, Share2, ShieldCheck, Mail, CreditCard, ArrowRight, Activity } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-accent selection:text-black">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 glass border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <img src="/devforge-logo-white.svg" alt="DevForge" className="h-6 w-auto" />
            <span className="text-xl font-bold tracking-tighter border-l border-white/20 pl-3 uppercase">
              Invoice<span className="text-accent">Follow</span>
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
            <span>Smart Escalation Engine Active</span>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-b from-white to-white/50 bg-clip-text text-transparent uppercase">
            Stop Chasing Payments. <br className="hidden md:block" />
            Automate Your Recovery.
          </h1>
          <p className="text-lg md:text-xl text-neutral-400 max-w-2xl mx-auto mb-12">
            The world's first industrial-grade escalation sequence for SaaS and B2B. 
            Recover up to 94% of overdue invoices automatically.
          </p>

          {/* TIMELINE VISUAL (Escalation Chain) */}
          <div className="max-w-4xl mx-auto mb-16 relative">
            <div className="absolute top-1/2 left-0 w-full h-[1px] bg-white/10 -translate-y-1/2 z-0 hidden md:block"></div>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 relative z-10">
              <div className="glass p-4 rounded-xl border border-white/5 relative bg-black/60">
                <div className="text-[10px] font-mono text-neutral-500 mb-2 uppercase">Day 0</div>
                <div className="flex items-center gap-2 mb-2">
                  <Mail size={14} className="text-blue-400" />
                  <span className="text-xs font-bold">Friendly Invoice</span>
                </div>
                <div className="h-1 w-full bg-blue-500/20 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 w-full"></div>
                </div>
              </div>

              <div className="glass p-4 rounded-xl border border-white/5 relative bg-black/60">
                <div className="text-[10px] font-mono text-neutral-500 mb-2 uppercase">Day 7</div>
                <div className="flex items-center gap-2 mb-2">
                  <Bell size={14} className="text-amber-400" />
                  <span className="text-xs font-bold">First Reminder</span>
                </div>
                <div className="h-1 w-full bg-amber-500/20 rounded-full overflow-hidden">
                  <div className="h-full bg-amber-500 w-full"></div>
                </div>
              </div>

              <div className="glass p-4 rounded-xl border border-accent/20 relative bg-black/60 shadow-[0_0_20px_rgba(130,19,70,0.1)] scale-105">
                <div className="text-[10px] font-mono text-accent mb-2 uppercase">Day 15</div>
                <div className="flex items-center gap-2 mb-2">
                  <Zap size={14} className="text-accent" />
                  <span className="text-xs font-bold">Strict Follow-up</span>
                </div>
                <div className="h-1 w-full bg-accent/20 rounded-full overflow-hidden">
                  <div className="h-full bg-accent w-full animate-pulse"></div>
                </div>
              </div>

              <div className="glass p-4 rounded-xl border border-red-500/20 relative bg-black/60">
                <div className="text-[10px] font-mono text-neutral-500 mb-2 uppercase">Day 30</div>
                <div className="flex items-center gap-2 mb-2">
                  <ShieldCheck size={14} className="text-red-500" />
                  <span className="text-xs font-bold">Final Notice</span>
                </div>
                <div className="h-1 w-full bg-red-500/20 rounded-full overflow-hidden">
                  <div className="h-full bg-red-500 w-0"></div>
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/register" className="btn-primary px-10 py-4 text-lg">
              Start Recovery Sequence
            </Link>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="py-24 px-6 bg-white/[0.01] border-y border-white/5">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-xs font-bold uppercase tracking-widest text-accent mb-4">Cashflow Automation</h2>
            <h3 className="text-3xl md:text-5xl font-bold">Deploy in 3 simple steps.</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 text-center">
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <Share2 className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">1. Connect CRM</h4>
              <p className="text-neutral-400 text-sm">Integrate Stripe, QuickBooks, or upload CSV. We sync invoices in real-time.</p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <Clock className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">2. Define Escalation</h4>
              <p className="text-neutral-400 text-sm">Choose from pre-built industrial templates or create custom follow-up chains.</p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <CreditCard className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">3. Collect</h4>
              <p className="text-neutral-400 text-sm">Watch payments roll in as our engine handles the psychological pressure for you.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 px-6 border-t border-white/5 bg-white/[0.02]">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Scale your collection.</h2>
            <p className="text-neutral-400">Premium recovery tools for high-volume businesses.</p>
          </div>

          <div className="max-w-lg mx-auto">
            <div className="glass p-10 rounded-3xl border-2 border-accent relative flex flex-col overflow-hidden shadow-[0_0_50px_rgba(130,19,70,0.2)]">
              <div className="absolute top-0 right-0 bg-accent text-black text-[10px] font-bold px-4 py-1.5 uppercase tracking-widest rounded-bl-xl">
                Most Popular
              </div>
              <div className="mb-8">
                <h3 className="text-2xl font-bold mb-2">Growth Plan</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-5xl font-bold">$9.99</span>
                  <span className="text-neutral-400">/mo</span>
                </div>
                <p className="text-sm text-neutral-400 mt-4 leading-relaxed">
                  Full access to the automated recovery engine. Includes a 7-day free trial.
                </p>
              </div>
              <ul className="space-y-4 mb-10">
                {[
                  "Unlimited Invoices Tracking",
                  "Multi-Channel Sequences",
                  "AI-Powered Debt Risk Profiling",
                  "Custom Branding & White-label",
                  "API & Webhook Integrations",
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
        <p>&copy; 2024 InvoiceFollow. Part of the DevForge ecosystem.</p>
      </footer>
    </div>
  );
}

