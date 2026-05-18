"use client";
import Link from "next/link";
import { Check, Zap, Shield, BarChart3, ArrowRight, FileSpreadsheet, Download, Layers, RefreshCw } from "lucide-react";
import { useEffect, useState, useRef } from "react";

function FileCleanerDemo() {
  const [phase, setPhase] = useState<"idle" | "scanning" | "cleaning" | "done">("idle");
  const [progress, setProgress] = useState(0);
  const [nullsFixed, setNullsFixed] = useState(0);
  const [dupsFixed, setDupsFixed] = useState(0);
  const [formatsFixed, setFormatsFixed] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const TOTAL_NULLS = 3402;
  const TOTAL_DUPS = 847;
  const TOTAL_FORMATS = 312;
  const DURATION_MS = 3200;
  const TICK_MS = 40;

  function startDemo() {
    if (phase === "scanning" || phase === "cleaning") return;
    setPhase("scanning");
    setProgress(0);
    setNullsFixed(0);
    setDupsFixed(0);
    setFormatsFixed(0);

    let elapsed = 0;
    intervalRef.current = setInterval(() => {
      elapsed += TICK_MS;
      const pct = Math.min(elapsed / DURATION_MS, 1);
      setProgress(Math.round(pct * 100));
      setNullsFixed(Math.round(pct * TOTAL_NULLS));
      setDupsFixed(Math.round(pct * TOTAL_DUPS));
      setFormatsFixed(Math.round(pct * TOTAL_FORMATS));

      if (pct >= 0.3) setPhase("cleaning");

      if (pct >= 1) {
        clearInterval(intervalRef.current!);
        setPhase("done");
      }
    }, TICK_MS);
  }

  useEffect(() => () => { if (intervalRef.current) clearInterval(intervalRef.current); }, []);

  const isRunning = phase === "scanning" || phase === "cleaning";
  const isDone = phase === "done";

  return (
    <div className="max-w-3xl mx-auto mb-16 glass p-6 md:p-8 rounded-2xl border border-white/10 bg-black/50">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center">
            <FileSpreadsheet size={18} className="text-accent" />
          </div>
          <div className="text-left">
            <p className="text-[10px] font-mono text-neutral-500 uppercase tracking-tighter">Dataset</p>
            <p className="text-sm font-bold">sales_data_2024.csv</p>
          </div>
        </div>
        <div className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest transition-all ${
          isDone ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
          : isRunning ? "bg-accent/10 border border-accent/20 text-accent animate-pulse"
          : "bg-white/5 border border-white/10 text-neutral-400"
        }`}>
          {isDone ? "✓ Complete" : isRunning ? "Processing..." : "Ready"}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {[
          { label: "NULL values", total: TOTAL_NULLS, fixed: nullsFixed, color: "red" },
          { label: "Duplicates", total: TOTAL_DUPS, fixed: dupsFixed, color: "amber" },
          { label: "Format errors", total: TOTAL_FORMATS, fixed: formatsFixed, color: "orange" },
        ].map(({ label, total, fixed, color }) => (
          <div key={label} className="bg-black/40 rounded-xl p-3 border border-white/5">
            <p className="text-[9px] font-mono text-neutral-500 uppercase mb-1">{label}</p>
            <p className={`text-lg font-bold font-mono ${isDone ? "text-emerald-400" : isRunning ? `text-${color}-400` : "text-white"}`}>
              {isDone ? 0 : total - fixed}
            </p>
            {isRunning && (
              <p className="text-[9px] text-emerald-500 font-mono">↓ {fixed} fixed</p>
            )}
            {isDone && (
              <p className="text-[9px] text-emerald-500 font-mono">↓ {total} fixed</p>
            )}
          </div>
        ))}
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-[10px] font-mono text-neutral-500 uppercase mb-2">
          <span>{phase === "idle" ? "Awaiting job" : phase === "done" ? "Cleaning complete" : "Scanning & cleaning..."}</span>
          <span className={isDone ? "text-emerald-400" : "text-accent"}>{progress}%</span>
        </div>
        <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${isDone ? "bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.6)]" : "bg-accent shadow-[0_0_12px_rgba(130,19,70,0.6)]"}`}
            style={{ width: `${progress}%`, transition: "width 40ms linear" }}
          />
        </div>
      </div>

      {/* Result Row + Download */}
      {isDone && (
        <div className="mb-6 space-y-3">
          <div className="flex items-center justify-between p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20">
            <div className="text-left">
              <p className="text-xs font-mono text-neutral-400">Output file</p>
              <p className="text-sm font-bold text-emerald-400">✅ sales_data_2024_clean.csv</p>
            </div>
            <div className="text-right">
              <p className="text-xs font-mono text-neutral-400">Size reduction</p>
              <p className="text-sm font-bold text-emerald-400">4.2 MB → 1.1 MB</p>
            </div>
          </div>
          <button
            onClick={() => {
              const rows = [
                "id,name,email,signup_date,amount,status,country",
                "1,Alice Johnson,alice@example.com,2024-01-15,1250.00,paid,US",
                "2,Bob Martinez,bob@company.com,2024-01-16,890.50,paid,MX",
                "3,Carol Smith,carol@startup.io,2024-01-17,2100.00,paid,CA",
                "4,David Lee,david@agency.com,2024-01-18,450.00,paid,GB",
                "5,Emma Wilson,emma@tech.co,2024-01-19,3200.00,paid,AU",
                "6,Frank Brown,frank@dev.io,2024-01-20,780.00,paid,DE",
                "7,Grace Kim,grace@saas.com,2024-01-21,1560.00,paid,KR",
                "8,Henry Davis,henry@corp.net,2024-01-22,920.00,paid,US",
                "9,Isabel Ruiz,isabel@media.es,2024-01-23,340.00,paid,ES",
                "10,James Clark,james@fintech.io,2024-01-24,4100.00,paid,US"
              ];
              const blob = new Blob([rows.join("\n")], { type: "text/csv" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = "sales_data_2024_clean.csv";
              a.click();
              URL.revokeObjectURL(url);
            }}
            className="w-full py-3 rounded-xl font-bold text-sm bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 transition-all flex items-center justify-center gap-2"
          >
            <Download size={14} /> Download Clean File
          </button>
        </div>
      )}

      {/* CTA Button */}
      <button
        onClick={startDemo}
        disabled={isRunning}
        className={`w-full py-3 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 ${
          isRunning ? "bg-white/5 text-neutral-500 cursor-not-allowed"
          : isDone ? "bg-white/5 border border-white/10 text-neutral-400 hover:bg-white/10"
          : "bg-accent text-black hover:bg-accent/90"
        }`}
      >
        <RefreshCw size={14} className={isRunning ? "animate-spin" : ""} />
        {isDone ? "Run Again" : isRunning ? "Cleaning in progress..." : "▶ Run Demo — No signup needed"}
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
        
        <div className="max-w-6xl mx-auto w-full text-center mb-10 relative z-10">
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-b from-white to-white/50 bg-clip-text text-transparent uppercase">
            Industrial-Grade Data Cleaning
          </h1>
          <p className="text-lg md:text-xl text-neutral-400 max-w-2xl mx-auto mb-6">
            Transform chaotic payloads into ready-to-use intelligence. No more duplicates, nulls, or broken formats.
          </p>
          <div className="text-sm text-neutral-400 space-y-3 mt-6 mb-12 max-w-2xl mx-auto border border-white/5 bg-white/[0.02] p-6 rounded-xl text-left">
            <p><strong className="text-white">The Problem:</strong> Tired of wasting hours cleaning CSV files full of nulls and duplicates?</p>
            <p><strong className="text-white">The Solution:</strong> This tool processes and fixes anomalies blazingly fast using FastAPI.</p>
            <p><strong className="text-white">Who is it for:</strong> Ideal for data analysts and operations teams.</p>
          </div>


          {/* LIVE DEMO */}
          <FileCleanerDemo />

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/register" className="btn-primary px-10 py-4 text-lg shadow-[0_0_30px_rgba(130,19,70,0.4)]">
              Start 7-Day Free Trial
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
              <p className="text-neutral-400 text-sm">Drop CSV or Excel files up to 50MB. Clean data in seconds.</p>
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
              <p className="text-neutral-400 text-sm">Get your cleaned data instantly in CSV or Excel format.</p>
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
                  "Smart Duplicate Detection",
                  "Deep Duplicate Detection",
                  "CSV, Excel and JSON Support",
                  "Instant Download After Cleaning",
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
        <div className="max-w-4xl mx-auto flex flex-col gap-6">
          <div className="flex flex-wrap justify-center gap-6 text-neutral-400">
            <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
            <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
            <Link href="/refunds" className="hover:text-white transition-colors">Refund Policy</Link>
          </div>
          <div className="text-xs space-y-2">
            <p><strong>Soporte:</strong> <a href="mailto:support@devforgeapp.pro" className="hover:text-white transition-colors">support@devforgeapp.pro</a></p>
            <p><strong>Ubicación:</strong> Lima, Perú</p>
            <p><strong>Refunds:</strong> You have a 7-day free trial. Once the $9.99 monthly charge is processed, all sales are final and no refunds are issued.</p>
          </div>
          <p className="mt-4">&copy; 2024 FileCleaner. Part of the DevForge ecosystem.</p>
        </div>
      </footer>
    </div>
  );
}
