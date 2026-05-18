"use client";
import Link from "next/link";
import { Check, Search, Bell, BarChart2, Globe, Activity, TrendingDown } from "lucide-react";
import { useEffect, useState, useRef } from "react";

const PRICE_HISTORY = [
  { time: "08:00", price: 1399 },
  { time: "10:00", price: 1380 },
  { time: "12:00", price: 1420 },
  { time: "14:00", price: 1310 },
  { time: "16:00", price: 1290 },
  { time: "18:00", price: 1249 },
];

function PriceTrackrDemo() {
  const [visiblePoints, setVisiblePoints] = useState(1);
  const [alertVisible, setAlertVisible] = useState(false);
  const [alertDismissed, setAlertDismissed] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function startDemo() {
    setVisiblePoints(1);
    setAlertVisible(false);
    setAlertDismissed(false);
    let idx = 1;
    timerRef.current = setInterval(() => {
      idx++;
      setVisiblePoints(idx);
      if (idx >= PRICE_HISTORY.length) {
        clearInterval(timerRef.current!);
        setTimeout(() => setAlertVisible(true), 400);
      }
    }, 700);
  }

  useEffect(() => {
    startDemo();
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  const points = PRICE_HISTORY.slice(0, visiblePoints);
  const currentPrice = points[points.length - 1]?.price ?? 1399;
  const startPrice = PRICE_HISTORY[0].price;
  const drop = startPrice - currentPrice;
  const dropPct = ((drop / startPrice) * 100).toFixed(1);

  const svgPoints = points.map((p, i) => {
    const x = (i / (PRICE_HISTORY.length - 1)) * 360 + 20;
    const y = 100 - ((p.price - 1200) / 250) * 80;
    return `${x},${y}`;
  }).join(" ");

  const svgFill = points.map((p, i) => {
    const x = (i / (PRICE_HISTORY.length - 1)) * 360 + 20;
    const y = 100 - ((p.price - 1200) / 250) * 80;
    return `${x},${y}`;
  });
  const fillPath = svgFill.length > 1
    ? `M${svgFill[0]} L${svgFill.slice(1).join(" L")} L${svgFill[svgFill.length - 1].split(",")[0]},110 L${svgFill[0].split(",")[0]},110 Z`
    : "";

  return (
    <div className="max-w-4xl mx-auto mb-16 glass p-6 rounded-2xl border border-white/5 bg-black/40 relative overflow-hidden">
      {/* Price Drop Alert — normal flow, above header */}
      {alertVisible && !alertDismissed && (
        <div className="flex items-start gap-3 bg-accent/10 border border-accent/30 rounded-xl p-4 shadow-[0_0_30px_rgba(130,19,70,0.3)] backdrop-blur-md mb-5">
          <Bell size={16} className="text-accent mt-0.5 flex-shrink-0 animate-bounce" />
          <div className="flex-1 text-left">
            <p className="text-xs font-bold text-accent uppercase tracking-widest mb-0.5">🔔 Price Drop Alert — amazon.com/pro-laptop-2024</p>
            <p className="text-xs text-neutral-300">Price dropped from <span className="text-white font-bold">${startPrice.toLocaleString()}</span> to <span className="text-emerald-400 font-bold">${currentPrice.toLocaleString()}</span> — save <span className="text-emerald-400 font-bold">${drop} ({dropPct}%)</span></p>
          </div>
          <button onClick={() => setAlertDismissed(true)} className="text-neutral-500 hover:text-white text-xs ml-2">✕</button>
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center border border-white/10">
            <Globe size={20} className="text-neutral-400" />
          </div>
          <div className="text-left">
            <p className="text-[10px] font-mono text-neutral-500 uppercase tracking-tighter">Tracked URL</p>
            <p className="text-sm font-bold truncate max-w-[200px]">amazon.com/pro-laptop-2024</p>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap justify-end">
          <div className="px-3 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-[10px] font-bold uppercase tracking-widest">
            Live: ${currentPrice.toLocaleString()}
          </div>
          {visiblePoints >= PRICE_HISTORY.length && (
            <div className="px-3 py-1 rounded-md bg-accent/10 border border-accent/20 text-accent text-[10px] font-bold uppercase tracking-widest animate-pulse flex items-center gap-1">
              <TrendingDown size={10} /> Drop −{dropPct}%
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      <div className="h-44 relative mb-3">
        <svg viewBox="0 0 400 110" className="w-full h-full" preserveAspectRatio="none">
          <defs>
            <linearGradient id="pg2" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#821346" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#821346" stopOpacity="0" />
            </linearGradient>
          </defs>
          {fillPath && <path d={fillPath} fill="url(#pg2)" />}
          {svgPoints && (
            <polyline points={svgPoints} fill="none" stroke="#821346" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          )}
          {points.map((p, i) => {
            const x = (i / (PRICE_HISTORY.length - 1)) * 360 + 20;
            const y = 100 - ((p.price - 1200) / 250) * 80;
            return (
              <g key={i}>
                {i === points.length - 1 ? (
                  <>
                    <circle cx={x} cy={y} r="5" fill="#821346" className="animate-ping" opacity="0.4" />
                    <circle cx={x} cy={y} r="3" fill="#821346" />
                    <circle cx={x} cy={y} r="2" fill="#fff" />
                  </>
                ) : (
                  <circle cx={x} cy={y} r="2.5" fill="#821346" />
                )}
              </g>
            );
          })}
        </svg>
        {/* Grid */}
        <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
          {[0,1,2,3].map(i => <div key={i} className="border-t border-white/5 w-full" />)}
        </div>
      </div>

      {/* Time axis */}
      <div className="flex justify-between text-[10px] font-mono text-neutral-500 uppercase mb-5">
        {PRICE_HISTORY.map((p, i) => (
          <span key={i} className={i < visiblePoints ? "text-neutral-400" : "text-neutral-700"}>{p.time}</span>
        ))}
      </div>

      <button
        onClick={startDemo}
        className="w-full py-3 rounded-xl font-bold text-sm bg-white/5 border border-white/10 text-neutral-300 hover:bg-white/10 hover:text-white transition-all flex items-center justify-center gap-2"
      >
        <Activity size={14} /> Replay Simulation
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
          <p className="text-lg md:text-xl text-neutral-400 max-w-2xl mx-auto mb-6">
            Monitor thousands of URLs with 10-minute refresh rates. 
            Detect price drops, stock changes, and market shifts before anyone else.
          </p>
          <div className="text-sm text-neutral-400 space-y-3 mt-6 mb-12 max-w-2xl mx-auto border border-white/5 bg-white/[0.02] p-6 rounded-xl text-left">
            <p><strong className="text-white">The Problem:</strong> Tired of manually checking your competitors' prices every day?</p>
            <p><strong className="text-white">The Solution:</strong> This tool monitors URLs in the background and alerts you to price changes.</p>
            <p><strong className="text-white">Who is it for:</strong> Ideal for e-commerce owners, dropshippers, and market strategists.</p>
          </div>


          {/* LIVE DEMO */}
          <PriceTrackrDemo />

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
              <p className="text-neutral-400 text-sm">Paste URLs from any marketplace. We detect price and stock status automatically.</p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                <Bell className="text-accent" size={32} />
              </div>
              <h4 className="text-xl font-bold mb-3">2. Detect Changes</h4>
              <p className="text-neutral-400 text-sm">We scan daily and alert you instantly on changes. Get instant email alerts when a price drops or stock changes.</p>
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
                  Automated daily price tracking with instant email alerts. Includes a 7-day free trial.
                </p>
              </div>
              <ul className="space-y-4 mb-10">
                {[
                  "Unlimited Tracked Products",
                  "Daily Automatic Price Checks",
                  "Historical Price Charts",
                  "Price History Tracking",
                  "Email Alerts on Price Drop",
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
          <p className="mt-4">&copy; 2024 PriceTrackr. Part of the DevForge ecosystem.</p>
        </div>
      </footer>
    </div>
  );
}
