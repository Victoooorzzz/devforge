"use client";
import Link from "next/link";
import { Check, Zap, Shield, BarChart3, ArrowRight, FileSpreadsheet, Download, Layers } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-accent selection:text-black">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 glass border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <img src="/devforge-logo-white.svg" alt="DevForge" className="h-6 w-auto" />
            <span className="text-xl font-bold tracking-tighter border-l border-white/20 pl-3">
              File<span className="text-accent">Cleaner</span>
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
        
        <div className="max-w-6xl mx-auto w-full text-center mb-16 relative z-10">
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-b from-white to-white/50 bg-clip-text text-transparent uppercase">
            Industrial-Grade Data Cleaning
          </h1>
          <p className="text-lg md:text-xl text-neutral-400 max-w-2xl mx-auto mb-12">
            Transform chaotic payloads into ready-to-use intelligence. No more duplicates, nulls, or broken formats.
          </p>
          
          {/* BEFORE -> AFTER VISUAL */}
          <div className="flex flex-col md:flex-row items-center justify-center gap-8 md:gap-16 mb-16">
            <div className="glass p-6 rounded-xl border border-red-500/20 w-64 text-left relative">
              <div className="absolute -top-3 -right-3 bg-red-500 text-[10px] font-bold px-2 py-0.5 rounded-full">MESSY</div>
              <p className="text-xs font-mono text-neutral-500 mb-2">📄 messy.csv</p>
              <div className="space-y-1 text-sm font-mono">
                <p className="text-white">12,453 rows</p>
                <p className="text-red-400">NULL: 3,402</p>
                <p className="text-red-400">Duplicates: 847</p>
                <p className="text-red-400">Format: MIXED</p>
                <p className="mt-4 text-neutral-500 line-through">4.2 MB</p>
              </div>
            </div>
            
            <div className="hidden md:block">
              <ArrowRight className="text-accent animate-pulse" size={48} />
            </div>

            <div className="glass p-6 rounded-xl border border-emerald-500/20 w-64 text-left relative">
              <div className="absolute -top-3 -right-3 bg-emerald-500 text-[10px] font-bold px-2 py-0.5 rounded-full">CLEAN</div>
              <p className="text-xs font-mono text-neutral-500 mb-2">✅ clean.csv</p>
              <div className="space-y-1 text-sm font-mono">
                <p className="text-white">12,453 rows</p>
                <p className="text-emerald-400">NULL: 0</p>
                <p className="text-emerald-400">Duplicates: 0</p>
                <p className="text-emerald-400">Format: ISO</p>
                <p className="mt-4 text-emerald-500 font-bold">1.1 MB</p>
              </div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/register" className="btn-primary px-10 py-4 text-lg">
              Try Live Demo — No signup required
            </Link>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="py-24 px-6 bg-white/[0.01] border-y border-white/5">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-xs font-bold uppercase tracking-widest text-accent mb-4">Process Workflow</h2>
            <h3 className="text-3xl md:text-5xl font-bold">Clean in 3 simple steps.</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 text-center">
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <FileSpreadsheet className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">1. Upload</h4>
              <p className="text-neutral-400 text-sm">Drop CSV or JSON files up to 50MB. We handle massive payloads with ease.</p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <Layers className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">2. Configure</h4>
              <p className="text-neutral-400 text-sm">Our AI automatically identifies issues. Use default rules or set custom filters.</p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <Download className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">3. Download</h4>
              <p className="text-neutral-400 text-sm">Get your cleaned data instantly in CSV, JSON, or Excel format.</p>
            </div>
          </div>
        </div>
      </section>

      {/* LIVE EXAMPLE */}
      <section className="py-24 px-6">
        <div className="max-w-4xl mx-auto glass p-8 md:p-12 rounded-3xl border border-white/10 relative overflow-hidden">
          <div className="flex flex-col md:flex-row items-center justify-between gap-8 relative z-10">
            <div>
              <p className="text-accent font-mono text-xs uppercase tracking-widest mb-2">Live Example</p>
              <h3 className="text-2xl font-bold mb-4">E-commerce dataset (demo)</h3>
              <div className="space-y-2 text-sm text-neutral-400 mb-8">
                <p>Original: 10,000 rows | <span className="text-emerald-400">Cleaned: 9,847 rows</span></p>
                <p>Issues found: <span className="text-amber-500">153</span></p>
              </div>
              <div className="flex gap-4">
                <button className="px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-xs font-bold transition-colors">View detailed report</button>
                <button className="px-4 py-2 bg-accent/20 text-accent hover:bg-accent/30 rounded-lg text-xs font-bold transition-colors">Download sample</button>
              </div>
            </div>
            <div className="w-full md:w-1/2 h-48 bg-black/40 rounded-xl border border-white/5 flex items-center justify-center">
              <BarChart3 className="text-white/10" size={64} />
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 px-6 border-t border-white/5 bg-white/[0.02]">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Simple, transparent pricing.</h2>
            <p className="text-neutral-400">Everything you need to keep your storage organized and clean.</p>
          </div>

          <div className="max-w-lg mx-auto">
            <div className="glass p-10 rounded-3xl border-2 border-accent relative flex flex-col overflow-hidden shadow-[0_0_50px_rgba(130,19,70,0.2)]">
              <div className="absolute top-0 right-0 bg-accent text-black text-[10px] font-bold px-4 py-1.5 uppercase tracking-widest rounded-bl-xl">
                Best Value
              </div>
              <div className="mb-8">
                <h3 className="text-2xl font-bold mb-2">Pro Access</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-5xl font-bold">$9.99</span>
                  <span className="text-neutral-400">/mo</span>
                </div>
                <p className="text-sm text-neutral-400 mt-4 leading-relaxed">
                  Unlock the full power of industrial-grade file cleaning. Includes a 7-day free trial.
                </p>
              </div>
              <ul className="space-y-4 mb-10">
                {[
                  "Unlimited File Cleanups",
                  "Advanced AI Cleanup Rules",
                  "Deep Duplicate Detection",
                  "API Access for Integrations",
                  "Priority 24/7 Support",
                  "50MB Max File Size"
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

      <footer className="py-12 px-6 border-t border-white/5 text-center text-neutral-500 text-sm">
        <p>&copy; 2024 FileCleaner. Part of the DevForge ecosystem.</p>
      </footer>
    </div>
  );
}
