"use client";
import Link from "next/link";
import { Check, Zap, Shield, BarChart3 } from "lucide-react";

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
      <section className="pt-24 pb-12 px-6 min-h-[85vh] flex flex-col justify-center">
        <div className="max-w-5xl mx-auto w-full flex flex-col items-center">
          <div className="text-center mb-8">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4 text-white">
              INDUSTRIAL-GRADE FILE CLEANER
            </h1>
            <p className="text-neutral-400 font-mono text-sm max-w-xl mx-auto uppercase tracking-widest">
              Drop your chaotic data payloads below.
            </p>
          </div>

          <div className="w-full relative group">
            {/* The Drop Zone */}
            <div className="w-full h-[55vh] flex flex-col items-center justify-center bg-[#0E0C0D] border-2 border-dashed border-[#821346] rounded-sm transition-all duration-300 relative overflow-hidden group-hover:bg-[#821346]/5">
              
              {/* Corner Accents */}
              <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-[#821346]"></div>
              <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-[#821346]"></div>
              <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-[#821346]"></div>
              <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-[#821346]"></div>

              <div className="absolute top-4 left-4 flex gap-2">
                <div className="w-2 h-2 rounded-full bg-neutral-600 animate-pulse"></div>
                <div className="w-2 h-2 rounded-full bg-neutral-600 animate-pulse delay-75"></div>
              </div>

              {/* Central Content */}
              <div className="flex flex-col items-center z-10">
                <div className="w-20 h-20 mb-6 rounded-full bg-[#191718] flex items-center justify-center border border-[#282627] shadow-[0_0_30px_rgba(130,19,70,0.3)]">
                  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#821346" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/></svg>
                </div>
                <h3 className="font-mono text-xl text-white mb-2 uppercase tracking-widest">Awaiting Payload</h3>
                <p className="text-neutral-500 text-sm mb-8 font-mono">Drag & drop files or click to browse</p>
                
                <div className="flex gap-4">
                  <Link href="/register" className="btn-primary px-8 py-3 text-sm">
                    Initialize System
                  </Link>
                </div>
              </div>

              {/* Decorative Scanline */}
              <div className="absolute top-0 left-0 w-full h-[2px] bg-[#821346]/40 shadow-[0_0_10px_#821346] animate-[scan_3s_ease-in-out_infinite]"></div>
            </div>

            {/* Badges / Status */}
            <div className="absolute -bottom-4 right-4 flex gap-2">
              <div className="bg-[#10B981]/10 border border-[#10B981]/30 text-[#10B981] px-3 py-1 text-xs font-mono rounded-sm flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-[#10B981]"></div>
                SYS_READY
              </div>
              <div className="bg-[#191718] border border-[#282627] text-neutral-400 px-3 py-1 text-xs font-mono rounded-sm">
                0 BYTES PROCESSED
              </div>
            </div>
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
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Simple, transparent pricing.</h2>
            <p className="text-neutral-400">Everything you need to keep your storage organized and clean.</p>
          </div>

          <div className="max-w-lg mx-auto">
            {/* Pro Plan - Single Option */}
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
                  "Unlimited Managed Storage",
                  "Advanced AI Cleanup Rules",
                  "Deep Duplicate Detection",
                  "Unlimited Connected Accounts",
                  "Priority 24/7 Support",
                  "Cloud Sync Integration"
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
        <p>&copy; 2024 FileCleaner. Part of the DevForge ecosystem.</p>
      </footer>
    </div>
  );
}
