"use client";
import Image from "next/image";
import Link from "next/link";
import { Check, MessageSquare, ThumbsUp, ThumbsDown, BarChart3, Share2, Activity } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

type FeedbackEntry = {
  text: string;
  sentiment: "positive" | "negative" | "neutral";
  score: number;
  themes: string[];
};

const FEEDBACK_QUEUE: FeedbackEntry[] = [
  {
    text: "The new performance update is incredible. My workflow is 2x faster now.",
    sentiment: "positive",
    score: 94,
    themes: ["#Performance", "#UX"],
  },
  {
    text: "Export feature keeps failing on large CSV files. Please fix this bug.",
    sentiment: "negative",
    score: 12,
    themes: ["#Bug", "#Export"],
  },
  {
    text: "Dashboard is clean but I wish there was a dark mode option.",
    sentiment: "neutral",
    score: 50,
    themes: ["#UI", "#Feature-Request"],
  },
  {
    text: "The weekly theme summary saves me hours every week.",
    sentiment: "positive",
    score: 97,
    themes: ["#Themes", "#Productivity"],
  },
  {
    text: "Onboarding was confusing at first but support team was amazing.",
    sentiment: "neutral",
    score: 58,
    themes: ["#Onboarding", "#Support"],
  },
];

function FeedbackLensDemo() {
  const [processed, setProcessed] = useState<FeedbackEntry[]>([]);
  const [current, setCurrent] = useState<FeedbackEntry | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [done, setDone] = useState(false);
  const analyzingRef = useRef(false);
  const queueRef = useRef<FeedbackEntry[]>([...FEEDBACK_QUEUE]);

  const runAnalysis = useCallback(() => {
    if (analyzingRef.current) return;
    analyzingRef.current = true;
    setProcessed([]);
    setCurrent(null);
    setDone(false);
    setAnalyzing(true);
    queueRef.current = [...FEEDBACK_QUEUE];
    let i = 0;

    function processNext() {
      if (i >= FEEDBACK_QUEUE.length) {
        analyzingRef.current = false;
        setAnalyzing(false);
        setCurrent(null);
        setDone(true);
        return;
      }
      const entry = FEEDBACK_QUEUE[i];
      setCurrent(entry);
      setTimeout(() => {
        setProcessed(prev => [entry, ...prev]);
        setCurrent(null);
        i++;
        setTimeout(processNext, 400);
      }, 1100);
    }

    setTimeout(processNext, 300);
  }, []);

  useEffect(() => {
    runAnalysis();
  }, [runAnalysis]);

  const positiveCount = processed.filter(f => f.sentiment === "positive").length;
  const negativeCount = processed.filter(f => f.sentiment === "negative").length;
  const avgScore = processed.length ? Math.round(processed.reduce((a, f) => a + f.score, 0) / processed.length) : 0;

  const sentimentColor = {
    positive: "border-emerald-500/30 bg-emerald-500/5",
    negative: "border-red-500/30 bg-red-500/5",
    neutral: "border-blue-500/20 bg-blue-500/5",
  };
  const sentimentIcon = {
    positive: <ThumbsUp size={11} className="text-emerald-400 flex-shrink-0" />,
    negative: <ThumbsDown size={11} className="text-red-400 flex-shrink-0" />,
    neutral: <MessageSquare size={11} className="text-blue-400 flex-shrink-0" />,
  };
  const sentimentLabel = {
    positive: "text-emerald-400",
    negative: "text-red-400",
    neutral: "text-blue-400",
  };

  return (
    <div className="max-w-4xl mx-auto mb-16 glass p-6 md:p-8 rounded-2xl border border-white/10 bg-black/50">
      {/* Stats Bar */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-black/40 rounded-xl p-3 border border-white/5 text-center">
          <p className="text-[9px] font-mono text-neutral-500 uppercase mb-1">Processed</p>
          <p className="text-xl font-bold font-mono text-white">{processed.length}<span className="text-neutral-600">/{FEEDBACK_QUEUE.length}</span></p>
        </div>
        <div className="bg-black/40 rounded-xl p-3 border border-white/5 text-center">
          <p className="text-[9px] font-mono text-neutral-500 uppercase mb-1">Avg Score</p>
          <p className={`text-xl font-bold font-mono ${avgScore >= 60 ? "text-emerald-400" : avgScore >= 40 ? "text-amber-400" : "text-red-400"}`}>
            {processed.length ? avgScore : "—"}
          </p>
        </div>
        <div className="bg-black/40 rounded-xl p-3 border border-white/5 text-center">
          <p className="text-[9px] font-mono text-neutral-500 uppercase mb-1">Bugs Found</p>
          <p className="text-xl font-bold font-mono text-red-400">{negativeCount}</p>
        </div>
      </div>

      {/* Analyzing indicator */}
      {current && (
        <div className="mb-4 p-4 rounded-xl border border-accent/30 bg-accent/5 flex items-start gap-3 animate-pulse">
          <Activity size={16} className="text-accent mt-0.5 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-[10px] font-mono text-accent uppercase tracking-widest mb-1">Analyzing...</p>
            <p className="text-xs text-neutral-300 italic truncate">&ldquo;{current.text}&rdquo;</p>
            <div className="mt-2 h-1 w-full bg-white/5 rounded-full overflow-hidden">
              <div className="h-full bg-accent animate-[shimmer_1.5s_infinite] w-3/4" />
            </div>
          </div>
        </div>
      )}

      {/* Results list */}
      <div className="space-y-2 max-h-64 overflow-y-auto mb-5 pr-1">
        {processed.length === 0 && !current && !analyzing && !done && (
          <p className="text-[10px] font-mono text-neutral-600 text-center py-8">No feedback analyzed yet.</p>
        )}
        {processed.map((entry, i) => (
          <div key={i} className={`flex gap-3 items-start p-3 rounded-xl border text-left transition-all ${sentimentColor[entry.sentiment]}`}>
            <div className="mt-0.5">{sentimentIcon[entry.sentiment]}</div>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-neutral-300 italic truncate">&ldquo;{entry.text}&rdquo;</p>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <span className={`text-[9px] font-bold uppercase ${sentimentLabel[entry.sentiment]}`}>
                  Score: {entry.score}/100
                </span>
                {entry.themes.map(t => (
                  <span key={t} className="text-[8px] px-1.5 py-0.5 rounded-full bg-white/5 text-neutral-500 border border-white/5">{t}</span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Sentiment summary bar */}
      {processed.length > 0 && (
        <div className="mb-5">
          <div className="flex justify-between text-[9px] font-mono text-neutral-500 uppercase mb-1.5">
            <span>Sentiment breakdown</span>
            <span>{positiveCount} positive · {negativeCount} negative</span>
          </div>
          <div className="w-full h-2 rounded-full bg-white/5 overflow-hidden flex">
            <div
              className="h-full bg-emerald-500 transition-all duration-500"
              style={{ width: `${(positiveCount / processed.length) * 100}%` }}
            />
            <div
              className="h-full bg-red-500 transition-all duration-500"
              style={{ width: `${(negativeCount / processed.length) * 100}%` }}
            />
            <div className="h-full bg-blue-500 flex-1 transition-all duration-500" />
          </div>
        </div>
      )}

      <button
        onClick={runAnalysis}
        disabled={analyzing}
        className={`w-full py-3 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 ${
          analyzing ? "bg-white/5 text-neutral-500 cursor-not-allowed"
          : "bg-accent text-black hover:bg-accent/90"
        }`}
      >
        <Activity size={14} />
        {analyzing ? "Analyzing feedback..." : done ? "Re-run review" : "Analyze Demo Feedback"}
      </button>
    </div>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-accent selection:text-black">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 glass border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <Image src="/devforge-logo-white.svg" alt="DevForge" width={118} height={24} className="h-6 w-auto" priority />
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
            <span>Local Feedback Engine Online</span>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-b from-white to-white/50 bg-clip-text text-transparent uppercase">
            Understand What Users <br className="hidden md:block" />
            Really Think.
          </h1>
          <p className="text-lg md:text-xl text-neutral-400 max-w-2xl mx-auto mb-6">
            A production-ready feedback triage engine for product teams.
            Transform reviews, tickets, and comments into sentiment, themes, and urgent issues.
          </p>
          <div className="text-sm text-neutral-400 space-y-3 mt-6 mb-12 max-w-2xl mx-auto border border-white/5 bg-white/[0.02] p-6 rounded-xl text-left">
            <p><strong className="text-white">The Problem:</strong> Tired of reading thousands of user reviews without finding the core issue?</p>
            <p><strong className="text-white">The Solution:</strong> This tool extracts common complaints, sentiment, and near-duplicates with local rules and VADER scoring.</p>
            <p><strong className="text-white">Who is it for:</strong> Ideal for Product Managers, support teams, and SaaS founders.</p>
          </div>


          {/* LIVE DEMO */}
          <FeedbackLensDemo />

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
              <p className="text-neutral-400 text-sm">Paste feedback text or upload a CSV. No integrations required to get started.</p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <Activity className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">2. Analyze</h4>
              <p className="text-neutral-400 text-sm">Local sentiment scoring extracts themes, identifies duplicates, and prioritizes urgent bug reports automatically.</p>
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
            <p className="text-neutral-400">Practical analytics for data-driven product organizations.</p>
          </div>

          <div className="max-w-lg mx-auto">
            <div className="glass p-10 rounded-3xl border-2 border-accent relative flex flex-col overflow-hidden shadow-[0_0_50px_rgba(130,19,70,0.2)]">
              <div className="absolute top-0 right-0 bg-accent text-black text-[10px] font-bold px-4 py-1.5 uppercase tracking-widest rounded-bl-xl">
                Pro
              </div>
              <div className="mb-8">
                <h3 className="text-2xl font-bold mb-2">Lens Pro</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-5xl font-bold">$19</span>
                  <span className="text-neutral-400">/mo</span>
                </div>
                <p className="text-sm text-neutral-400 mt-4 leading-relaxed">
                  5000 feedback items per month with local sentiment, clustering, external sources, and a 7-day free trial.
                </p>
              </div>
              <ul className="space-y-4 mb-10">
                {[
                  "5000 Feedback Items/Month",
                  "Advanced Theme Extraction",
                  "Urgency & Bug Detection",
                  "Weekly Summary Reports",
                  "Draft Reply Generator",
                  "GitHub, Canny, X, and Reddit Sources"
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
        <div className="max-w-4xl mx-auto flex flex-col gap-6">
          <div className="flex flex-wrap justify-center gap-6 text-neutral-400">
            <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
            <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
            <Link href="/refunds" className="hover:text-white transition-colors">Refund Policy</Link>
          </div>
          <div className="text-xs space-y-2">
            <p><strong>Soporte:</strong> <a href="mailto:support@devforgeapp.pro" className="hover:text-white transition-colors">support@devforgeapp.pro</a></p>
            <p><strong>Ubicación:</strong> Lima, Perú</p>
            <p><strong>Refunds:</strong> You have a 7-day free trial. Once the $19 monthly charge is processed, all sales are final and no refunds are issued.</p>
          </div>
          <p className="mt-4">&copy; 2024 FeedbackLens. Part of the DevForge ecosystem.</p>
        </div>
      </footer>
    </div>
  );
}
