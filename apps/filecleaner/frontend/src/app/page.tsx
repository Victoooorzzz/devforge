"use client";
import Link from "next/link";
import { Check, Zap, Shield, BarChart3 } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-accent selection:text-black">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 glass border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="text-xl font-bold tracking-tighter">
            File<span className="text-accent">Cleaner</span>
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
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 text-accent text-xs font-medium mb-6">
            <Zap size={14} />
            <span>Automated Storage Management</span>
          </div>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-b from-white to-white/50 bg-clip-text text-transparent">
            Keep your storage lean and organized.
          </h1>
          <p className="text-lg md:text-xl text-neutral-400 mb-10 max-w-2xl mx-auto">
            Automate file cleanup, detect duplicates, and classify documents with AI-powered storage management.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/register" className="btn-primary px-8 py-4 text-lg w-full sm:w-auto text-center">
              Start Free Trial
            </Link>
            <Link href="#features" className="px-8 py-4 text-lg font-medium text-neutral-400 hover:text-white transition-colors">
              See How It Works →
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-6 border-t border-white/5">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="glass p-8 rounded-2xl border border-white/5">
              <Shield className="text-accent mb-4" size={32} />
              <h3 className="text-xl font-bold mb-3">Auto-Cleanup</h3>
              <p className="text-neutral-400 text-sm leading-relaxed">
                Set rules to automatically delete temporary files, old downloads, and system cache based on age or size.
              </p>
            </div>
            <div className="glass p-8 rounded-2xl border border-white/5">
              <BarChart3 className="text-accent mb-4" size={32} />
              <h3 className="text-xl font-bold mb-3">Duplicate Detection</h3>
              <p className="text-neutral-400 text-sm leading-relaxed">
                Our smart engine identifies exact and near-duplicate files across all your connected storage accounts.
              </p>
            </div>
            <div className="glass p-8 rounded-2xl border border-white/5">
              <Zap className="text-accent mb-4" size={32} />
              <h3 className="text-xl font-bold mb-3">AI Classification</h3>
              <p className="text-neutral-400 text-sm leading-relaxed">
                Automatically sort documents, images, and videos into organized folders using advanced file recognition.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 px-6 border-t border-white/5 bg-white/[0.02]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Simple, transparent pricing.</h2>
            <p className="text-neutral-400">Choose the plan that fits your storage needs.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Starter */}
            <div className="glass p-10 rounded-3xl border border-white/10 flex flex-col">
              <div className="mb-8">
                <h3 className="text-xl font-bold mb-2">Starter</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-bold">$9</span>
                  <span className="text-neutral-400">/mo</span>
                </div>
                <p className="text-sm text-neutral-400 mt-4">Perfect for personal use and small setups.</p>
              </div>
              <ul className="space-y-4 mb-10 flex-1">
                {["Up to 500GB Managed", "Basic Cleanup Rules", "Duplicate Detection", "1 Storage Account", "Email Support"].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-sm text-neutral-300">
                    <Check size={16} className="text-accent" /> {item}
                  </li>
                ))}
              </ul>
              <Link href="/register?plan=starter" className="btn-primary py-4 text-center">
                Start 14-Day Free Trial
              </Link>
            </div>

            {/* Pro */}
            <div className="glass p-10 rounded-3xl border-2 border-accent/50 relative flex flex-col overflow-hidden">
              <div className="absolute top-0 right-0 bg-accent text-black text-[10px] font-bold px-3 py-1 uppercase tracking-widest rounded-bl-xl">
                Most Popular
              </div>
              <div className="mb-8">
                <h3 className="text-xl font-bold mb-2">Pro</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-bold">$19</span>
                  <span className="text-neutral-400">/mo</span>
                </div>
                <p className="text-sm text-neutral-400 mt-4">Advanced management for heavy storage users.</p>
              </div>
              <ul className="space-y-4 mb-10 flex-1">
                {["Unlimited Storage", "Custom AI Rules", "Advanced File Insights", "Unlimited Accounts", "Priority 24/7 Support", "Cloud Sync Support"].map((item) => (
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
        <p>&copy; 2024 FileCleaner. Part of the DevForge ecosystem.</p>
      </footer>
    </div>
  );
}
