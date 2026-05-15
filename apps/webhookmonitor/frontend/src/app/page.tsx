"use client";
import Link from "next/link";
import { Check, Eye, Server, RefreshCcw, Activity } from "lucide-react";
import { useEffect, useState, useRef } from "react";

type WebhookEvent = {
  id: string;
  time: string;
  method: "POST" | "GET";
  path: string;
  status: number;
  detail?: string;
  detailColor?: string;
  payload?: string;
};

const INITIAL_EVENTS: WebhookEvent[] = [
  {
    id: "e1",
    time: "14:02:11",
    method: "POST",
    path: "/api/webhooks/stripe",
    status: 200,
    payload: `{ "type": "payment_intent.succeeded", "amount": 9900, "currency": "usd" }`,
  },
  {
    id: "e2",
    time: "14:02:15",
    method: "POST",
    path: "/api/webhooks/github",
    status: 500,
    detail: "→ Critical: Webhook signature verification failed.",
    detailColor: "text-red-400",
  },
];

const STREAM_EVENTS: WebhookEvent[] = [
  {
    id: "e3",
    time: "14:03:02",
    method: "POST",
    path: "/api/webhooks/shopify",
    status: 200,
    payload: `{ "topic": "orders/create", "order_id": 50312, "total": "149.00" }`,
  },
  {
    id: "e4",
    time: "14:03:44",
    method: "POST",
    path: "/api/webhooks/stripe",
    status: 200,
    payload: `{ "type": "customer.subscription.updated", "plan": "pro" }`,
  },
  {
    id: "e5",
    time: "14:04:11",
    method: "POST",
    path: "/api/webhooks/github",
    status: 200,
    payload: `{ "action": "push", "ref": "refs/heads/main", "commits": 3 }`,
  },
  {
    id: "e6",
    time: "14:04:58",
    method: "POST",
    path: "/api/webhooks/stripe",
    status: 422,
    detail: "→ Error: Invalid payload schema — missing `customer_id`.",
    detailColor: "text-amber-400",
  },
];

function WebhookMonitorDemo() {
  const [events, setEvents] = useState<WebhookEvent[]>(INITIAL_EVENTS);
  const [streaming, setStreaming] = useState(false);
  const [streamIdx, setStreamIdx] = useState(0);
  const [cursor, setCursor] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const cursorRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    cursorRef.current = setInterval(() => setCursor(p => !p), 500);
    return () => {
      if (cursorRef.current) clearInterval(cursorRef.current);
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  function startStream() {
    if (streaming) return;
    setStreaming(true);
    setEvents(INITIAL_EVENTS);
    setStreamIdx(0);
    let idx = 0;
    timerRef.current = setInterval(() => {
      const event = STREAM_EVENTS[idx];
      if (!event) {
        clearInterval(timerRef.current!);
        setStreaming(false);
        return;
      }
      setEvents(prev => [...prev, event]);
      idx++;
      if (idx >= STREAM_EVENTS.length) {
        clearInterval(timerRef.current!);
        setStreaming(false);
        setStreamIdx(STREAM_EVENTS.length);
      }
    }, 1100);
  }

  function reset() {
    if (timerRef.current) clearInterval(timerRef.current);
    setEvents(INITIAL_EVENTS);
    setStreaming(false);
    setStreamIdx(0);
  }

  return (
    <div className="max-w-4xl mx-auto mb-16 relative group">
      <div className="absolute inset-0 bg-accent/10 blur-3xl rounded-full opacity-0 group-hover:opacity-60 transition-opacity duration-1000" />

      <div className="relative glass rounded-xl border border-white/10 bg-black/60 overflow-hidden shadow-2xl">
        {/* Title Bar */}
        <div className="bg-white/5 border-b border-white/5 px-4 py-2 flex items-center justify-between">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/50" />
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500/50" />
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/50" />
          </div>
          <div className="text-[10px] font-mono text-neutral-500 uppercase tracking-widest">devforge-monitor --stream</div>
          <div className="flex gap-2">
            <div className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${streaming ? "bg-accent/20 text-accent animate-pulse" : "bg-white/5 text-neutral-500"}`}>
              {streaming ? "● live" : "● idle"}
            </div>
          </div>
        </div>

        {/* Terminal Body */}
        <div className="p-5 font-mono text-xs text-left space-y-3 min-h-[280px] max-h-[320px] overflow-y-auto">
          {events.map((ev) => (
            <div key={ev.id} className="space-y-1 animate-[fadeIn_0.3s_ease]">
              <div className="flex gap-3 items-center flex-wrap">
                <span className="text-neutral-500">{ev.time}</span>
                <span className="text-emerald-400">{ev.method}</span>
                <span className="text-white">{ev.path}</span>
                <span className={`ml-auto font-bold ${ev.status >= 500 ? "text-red-500" : ev.status >= 400 ? "text-amber-400" : "text-emerald-500"}`}>
                  {ev.status} {ev.status >= 500 ? "ERR" : ev.status >= 400 ? "WARN" : "OK"}
                </span>
              </div>
              {ev.payload && (
                <div className="pl-4 text-neutral-500 border-l border-white/5 text-[10px] truncate">
                  <span className="text-accent">{"{"}</span> {ev.payload.replace(/[{}]/g, "").trim()} <span className="text-accent">{"}"}</span>
                </div>
              )}
              {ev.detail && (
                <div className={`pl-4 text-[10px] italic ${ev.detailColor ?? "text-neutral-400"}`}>{ev.detail}</div>
              )}
            </div>
          ))}

          <div className="flex gap-3 mt-4">
            <span className="text-accent">&gt;</span>
            <span className="text-white">Waiting for incoming requests...</span>
            <div className={`w-1.5 h-3.5 bg-accent ${cursor ? "opacity-100" : "opacity-0"} transition-opacity`} />
          </div>
          <div ref={bottomRef} />
        </div>

        {/* Footer Bar */}
        <div className="bg-white/5 border-t border-white/5 px-4 py-2 flex items-center justify-between">
          <span className="text-[9px] font-mono text-neutral-500">
            {events.length} events captured — {events.filter(e => e.status >= 400).length} errors
          </span>
          <div className="flex gap-2">
            <button
              onClick={reset}
              className="text-[9px] font-bold text-neutral-500 hover:text-white transition-colors px-2 py-0.5 rounded border border-white/5 hover:border-white/20"
            >
              Clear
            </button>
            <button
              onClick={startStream}
              disabled={streaming}
              className={`text-[9px] font-bold px-3 py-0.5 rounded transition-all ${
                streaming ? "bg-white/5 text-neutral-500 cursor-not-allowed"
                : "bg-accent text-black hover:bg-accent/90"
              }`}
            >
              {streaming ? "Streaming..." : streamIdx > 0 ? "▶ Replay" : "▶ Simulate incoming"}
            </button>
          </div>
        </div>
      </div>
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

          {/* LIVE DEMO */}
          <WebhookMonitorDemo />

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
              <p className="text-neutral-400 text-sm">Replay failed requests and search across all logs directly from the dashboard.</p>
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
                  "Live Payload Inspector",
                  "Full Request History",
                  "Manual Replay from Dashboard",
                  "Universal Search Across Logs",
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
