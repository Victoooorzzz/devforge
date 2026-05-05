"use client";
import Link from "next/link";
import { Check, Zap, MessageSquare, ThumbsUp, ThumbsDown, BarChart3, Brain, Share2, ArrowRight, Activity } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-accent selection:text-black">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 glass border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <img src="/devforge-logo-white.svg" alt="DevForge" className="h-6 w-auto" />
            <span className="text-xl font-bold tracking-tighter border-l border-white/20 pl-3 uppercase">
              Feedback<span className="text-accent">Lens</span>
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
            <span>AI Feedback Engine Online</span>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-b from-white to-white/50 bg-clip-text text-transparent uppercase">
            Understand What Users <br className="hidden md:block" />
            Really Think.
          </h1>
          <p className="text-lg md:text-xl text-neutral-400 max-w-2xl mx-auto mb-12">
            The world's first industrial-grade sentiment analysis engine for elite product teams. 
            Transform thousands of reviews into actionable intelligence in seconds.
          </p>

          {/* SENTIMENT VISUAL */}
          <div className="max-w-4xl mx-auto mb-16 relative">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10">
              <div className="glass p-6 rounded-xl border border-emerald-500/20 text-left bg-black/60 transform -rotate-2">
                <div className="flex items-center gap-2 mb-3">
                  <ThumbsUp size={16} className="text-emerald-500" />
                  <span className="text-[10px] font-bold text-emerald-500 uppercase">Positive Sentiment</span>
                </div>
                <p className="text-xs text-neutral-400 italic mb-4">"The new performance update is incredible. My workflow is 2x faster now."</p>
                <div className="flex gap-2">
                  <span className="text-[9px] px-2 py-0.5 rounded-full bg-white/5 text-neutral-500 border border-white/5">#UX</span>
                  <span className="text-[9px] px-2 py-0.5 rounded-full bg-white/5 text-neutral-500 border border-white/5">#Speed</span>
                </div>
              </div>

              <div className="glass p-8 rounded-xl border border-accent/30 text-center bg-black/80 scale-110 z-20 shadow-[0_0_40px_rgba(130,19,70,0.2)]">
                <Brain className="text-accent mx-auto mb-4 animate-pulse" size={40} />
                <h4 className="text-sm font-bold uppercase tracking-widest mb-2">Analyzing Themes</h4>
                <div className="space-y-2">
                  <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full bg-accent w-3/4 animate-[shimmer_2s_infinite]"></div>
                  </div>
                  <p className="text-[10px] font-mono text-neutral-500 uppercase">Processing 1,402 entries...</p>
                </div>
              </div>

              <div className="glass p-6 rounded-xl border border-red-500/20 text-left bg-black/60 transform rotate-2">
                <div className="flex items-center gap-2 mb-3">
                  <ThumbsDown size={16} className="text-red-500" />
                  <span className="text-[10px] font-bold text-red-500 uppercase">Negative Sentiment</span>
                </div>
                <p className="text-xs text-neutral-400 italic mb-4">"The export feature keeps failing on large CSV files. Please fix this bug."</p>
                <div className="flex gap-2">
                  <span className="text-[9px] px-2 py-0.5 rounded-full bg-white/5 text-neutral-500 border border-white/5">#Bug</span>
                  <span className="text-[9px] px-2 py-0.5 rounded-full bg-white/5 text-neutral-500 border border-white/5">#Export</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/register" className="btn-primary px-10 py-4 text-lg">
              Start Analysis Sequence
            </Link>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="py-24 px-6 bg-white/[0.01] border-y border-white/5">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-xs font-bold uppercase tracking-widest text-accent mb-4">Intelligence Pipeline</h2>
            <h3 className="text-3xl md:text-5xl font-bold">Listen in 3 simple steps.</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 text-center">
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <Share2 className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">1. Collect</h4>
              <p className="text-neutral-400 text-sm">Import feedback from App Store, Play Store, Slack, or via our universal API endpoint.</p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <Brain className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">2. Analyze</h4>
              <p className="text-neutral-400 text-sm">Our AI extracts core themes, sentiment intensity, and prioritizes urgent bug reports automatically.</p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <BarChart3 className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">3. Optimize</h4>
              <p className="text-neutral-400 text-sm">Build your roadmap based on real user evidence, not gut feeling. Track improvements over time.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 px-6 border-t border-white/5 bg-white/[0.02]">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Actionable intelligence.</h2>
            <p className="text-neutral-400">Premium analytics for data-driven product organizations.</p>
          </div>

          <div className="max-w-lg mx-auto">
            <div className="glass p-10 rounded-3xl border-2 border-accent relative flex flex-col overflow-hidden shadow-[0_0_50px_rgba(130,19,70,0.2)]">
              <div className="absolute top-0 right-0 bg-accent text-black text-[10px] font-bold px-4 py-1.5 uppercase tracking-widest rounded-bl-xl">
                Unlimited
              </div>
              <div className="mb-8">
                <h3 className="text-2xl font-bold mb-2">Lens Pro</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-5xl font-bold">$9.99</span>
                  <span className="text-neutral-400">/mo</span>
                </div>
                <p className="text-sm text-neutral-400 mt-4 leading-relaxed">
                  Full access to the sentiment engine and theme clustering. Includes a 7-day free trial.
                </p>
              </div>
              <ul className="space-y-4 mb-10">
                {[
                  "Unlimited Feedback Processing",
                  "Advanced Theme Extraction",
                  "Urgency & Bug Detection",
                  "Multi-Channel Dashboard",
                  "API & Webhook Access",
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
        <p>&copy; 2024 FeedbackLens. Part of the DevForge ecosystem.</p>
      </footer>
    </div>
  );
}
