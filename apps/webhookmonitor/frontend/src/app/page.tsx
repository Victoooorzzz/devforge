"use client";
import Link from "next/link";
import { Check, Zap, Eye, ShieldCheck, Terminal, Server, RefreshCcw, Code, ArrowRight, Activity } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-accent selection:text-black">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 glass border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <img src="/devforge-logo-white.svg" alt="DevForge" className="h-6 w-auto" />
            <span className="text-xl font-bold tracking-tighter border-l border-white/20 pl-3 uppercase">
              Webhook<span className="text-accent">Monitor</span>
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
            <span>Infrastructure Status: Operational</span>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-b from-white to-white/50 bg-clip-text text-transparent uppercase">
            Intercept, Inspect, <br className="hidden md:block" />
            and Replay Anything.
          </h1>
          <p className="text-lg md:text-xl text-neutral-400 max-w-2xl mx-auto mb-12 font-mono text-sm leading-relaxed">
            Developer-first webhook debugging. Stop guessing why your integrations fail. 
            Industrial-grade payload inspection for elite engineering teams.
          </p>

          {/* TERMINAL UI (Interactive Simulation) */}
          <div className="max-w-4xl mx-auto mb-16 relative group">
            <div className="absolute inset-0 bg-accent/10 blur-3xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-1000"></div>
            
            <div className="relative glass rounded-xl border border-white/10 bg-black/60 overflow-hidden shadow-2xl">
              {/* Terminal Title Bar */}
              <div className="bg-white/5 border-b border-white/5 px-4 py-2 flex items-center justify-between">
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500/40"></div>
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-500/40"></div>
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/40"></div>
                </div>
                <div className="text-[10px] font-mono text-neutral-500 uppercase tracking-widest">devforge-monitor --stream</div>
                <div className="w-10"></div>
              </div>

              {/* Terminal Body */}
              <div className="p-6 font-mono text-xs text-left space-y-4 min-h-[320px]">
                <div className="flex gap-4">
                  <span className="text-neutral-500">14:02:11</span>
                  <span className="text-emerald-400">POST</span>
                  <span className="text-white">/api/webhooks/stripe</span>
                  <span className="text-emerald-500 ml-auto font-bold">200 OK</span>
                </div>
                <div className="pl-16 text-neutral-400 border-l border-white/5 ml-4 pb-2">
                  <span className="text-accent">{"{"}</span> <br />
                  &nbsp;&nbsp;"type": "payment_intent.succeeded", <br />
                  &nbsp;&nbsp;"amount": 9900, <br />
                  &nbsp;&nbsp;"currency": "usd" <br />
                  <span className="text-accent">{"}"}</span>
                </div>

                <div className="flex gap-4">
                  <span className="text-neutral-500">14:02:15</span>
                  <span className="text-emerald-400">POST</span>
                  <span className="text-white">/api/webhooks/github</span>
                  <span className="text-red-500 ml-auto font-bold uppercase tracking-tighter">500 ERR</span>
                </div>
                <div className="pl-16 text-red-400/80 italic">
                  {"->"} Critical: Webhook signature verification failed.
                </div>

                <div className="flex gap-4 mt-6">
                  <span className="text-accent animate-pulse">{">"}</span>
                  <span className="text-white">Waiting for incoming requests...</span>
                  <div className="w-2 h-4 bg-accent animate-pulse"></div>
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/register" className="btn-primary px-10 py-4 text-lg">
              Initialize Debugger
            </Link>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="py-24 px-6 bg-white/[0.01] border-y border-white/5">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-xs font-bold uppercase tracking-widest text-accent mb-4">Pipeline Debugging</h2>
            <h3 className="text-3xl md:text-5xl font-bold">Trace in 3 simple steps.</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 text-center">
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <Server className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">1. Create Endpoint</h4>
              <p className="text-neutral-400 text-sm">Generate a secure, persistent URL for any provider (Stripe, GitHub, Shopify) in seconds.</p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <Eye className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">2. Live Debug</h4>
              <p className="text-neutral-400 text-sm">Inspect headers, payload, and signatures in our real-time terminal simulation.</p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <RefreshCcw className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">3. Auto-Retry</h4>
              <p className="text-neutral-400 text-sm">Configure automated retry logic and replay failed requests directly from the dashboard.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 px-6 border-t border-white/5 bg-white/[0.02]">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Infrastructure-grade access.</h2>
            <p className="text-neutral-400">Everything you need to ship stable integrations with confidence.</p>
          </div>

          <div className="max-w-lg mx-auto">
            <div className="glass p-10 rounded-3xl border-2 border-accent relative flex flex-col overflow-hidden shadow-[0_0_50px_rgba(130,19,70,0.2)]">
              <div className="absolute top-0 right-0 bg-accent text-black text-[10px] font-bold px-4 py-1.5 uppercase tracking-widest rounded-bl-xl">
                Infrastructure
              </div>
              <div className="mb-8">
                <h3 className="text-2xl font-bold mb-2">Enterprise Plan</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-5xl font-bold">$9.99</span>
                  <span className="text-neutral-400">/mo</span>
                </div>
                <p className="text-sm text-neutral-400 mt-4 leading-relaxed">
                  Full inspection and persistent webhook history. Includes a 7-day free trial.
                </p>
              </div>
              <ul className="space-y-4 mb-10">
                {[
                  "Unlimited Endpoints",
                  "Real-time Payload Streaming",
                  "90-Day History Retention",
                  "Advanced Retry Sequences",
                  "Custom Header Manipulation",
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
        <p>&copy; 2024 WebhookMonitor. Part of the DevForge ecosystem.</p>
      </footer>
    </div>
  );
}

