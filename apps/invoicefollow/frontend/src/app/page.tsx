"use client";
import Link from "next/link";
import { Check, Zap, Clock, Bell, Share2, ShieldCheck, Mail, CreditCard, Activity } from "lucide-react";
import { useEffect, useState, useRef } from "react";

const ESCALATION_STEPS = [
  {
    day: "Day 0",
    label: "Friendly Invoice",
    color: "blue",
    icon: "mail",
    status: "Sent",
    subject: "Invoice #1042 — $4,800 due",
    amount: "$4,800.00",
    response: "Delivered ✓",
    responseColor: "text-blue-400",
  },
  {
    day: "Day 7",
    label: "First Reminder",
    color: "amber",
    icon: "bell",
    status: "Sent",
    subject: "Gentle reminder: Invoice #1042",
    amount: "$4,800.00",
    response: "Opened ✓",
    responseColor: "text-amber-400",
  },
  {
    day: "Day 15",
    label: "Strict Follow-up",
    color: "accent",
    icon: "zap",
    status: "Active",
    subject: "URGENT: Invoice #1042 overdue",
    amount: "$4,800.00",
    response: "→ In progress",
    responseColor: "text-accent",
  },
  {
    day: "Day 30",
    label: "Final Notice",
    color: "red",
    icon: "shield",
    status: "Pending",
    subject: "Final notice before escalation",
    amount: "$4,800.00",
    response: "Awaiting trigger",
    responseColor: "text-neutral-500",
  },
];

function InvoiceFollowDemo() {
  const [activeStep, setActiveStep] = useState(2); // starts at "Strict Follow-up" (current active)
  const [animating, setAnimating] = useState(false);
  const [paid, setPaid] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function runSequence() {
    if (animating) return;
    setPaid(false);
    setActiveStep(0);
    setAnimating(true);
    let step = 0;
    timerRef.current = setInterval(() => {
      step++;
      if (step < ESCALATION_STEPS.length) {
        setActiveStep(step);
      } else {
        clearInterval(timerRef.current!);
        setTimeout(() => {
          setPaid(true);
          setAnimating(false);
        }, 600);
      }
    }, 1200);
  }

  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current); }, []);

  const iconMap: Record<string, React.ReactNode> = {
    mail: <Mail size={13} />,
    bell: <Bell size={13} />,
    zap: <Zap size={13} />,
    shield: <ShieldCheck size={13} />,
  };
  const colorBorder: Record<string, string> = {
    blue: "border-blue-500/30 shadow-[0_0_12px_rgba(59,130,246,0.1)]",
    amber: "border-amber-500/30 shadow-[0_0_12px_rgba(245,158,11,0.1)]",
    accent: "border-accent/30 shadow-[0_0_16px_rgba(130,19,70,0.2)]",
    red: "border-red-500/30 shadow-[0_0_12px_rgba(239,68,68,0.1)]",
  };
  const colorText: Record<string, string> = {
    blue: "text-blue-400",
    amber: "text-amber-400",
    accent: "text-accent",
    red: "text-red-400",
  };
  const colorBar: Record<string, string> = {
    blue: "bg-blue-500",
    amber: "bg-amber-500",
    accent: "bg-accent",
    red: "bg-red-500",
  };

  return (
    <div className="max-w-3xl mx-auto mb-16 glass p-6 md:p-8 rounded-2xl border border-white/10 bg-black/50">
      {/* Invoice header */}
      <div className="flex items-center justify-between mb-6">
        <div className="text-left">
          <p className="text-[10px] font-mono text-neutral-500 uppercase">Invoice #1042 — Acme Corp</p>
          <p className={`text-2xl font-bold font-mono ${paid ? "text-emerald-400" : "text-white"}`}>$4,800.00</p>
        </div>
        <div className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest transition-all ${
          paid ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
          : animating ? "bg-accent/10 border border-accent/20 text-accent animate-pulse"
          : "bg-amber-500/10 border border-amber-500/20 text-amber-400"
        }`}>
          {paid ? "✓ Payment Received" : animating ? "Escalating..." : "Overdue — Day 15"}
        </div>
      </div>

      {/* Steps */}
      <div className="relative mb-6">
        {/* Connector line */}
        <div className="absolute top-5 left-5 bottom-5 w-[1px] bg-white/5 z-0" />

        <div className="space-y-3 relative z-10">
          {ESCALATION_STEPS.map((step, i) => {
            const isActive = i === activeStep;
            const isPast = i < activeStep || paid;
            const isFuture = i > activeStep && !paid;
            return (
              <div
                key={i}
                className={`flex gap-4 items-start p-4 rounded-xl border transition-all duration-500 ${
                  isActive && !paid ? `${colorBorder[step.color]} bg-black/60 scale-[1.01]`
                  : isPast ? "border-white/5 bg-black/20"
                  : "border-white/5 bg-black/10 opacity-40"
                }`}
              >
                {/* Icon */}
                <div className={`w-10 h-10 rounded-full flex-shrink-0 flex items-center justify-center border transition-all ${
                  isPast && !isActive ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                  : isActive ? `bg-black/60 border-${step.color}-500/30 ${colorText[step.color]}`
                  : "bg-white/5 border-white/10 text-neutral-600"
                }`}>
                  {isPast && !isActive ? "✓" : iconMap[step.icon]}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-[9px] font-mono uppercase ${isActive ? colorText[step.color] : "text-neutral-500"}`}>{step.day}</span>
                      <span className="text-xs font-bold">{step.label}</span>
                    </div>
                    <span className={`text-[9px] font-mono ${isPast && !isActive ? "text-emerald-400" : isActive ? colorText[step.color] : "text-neutral-600"}`}>
                      {isPast && !isActive ? "Sent ✓" : step.response}
                    </span>
                  </div>
                  {(isActive || isPast) && (
                    <p className="text-[10px] text-neutral-500 font-mono truncate">{step.subject}</p>
                  )}
                  {isActive && (
                    <div className="mt-2 h-1 w-full bg-white/5 rounded-full overflow-hidden">
                      <div className={`h-full ${colorBar[step.color]} w-full animate-pulse`} />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {paid && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20 mb-5">
          <div className="text-2xl">🎉</div>
          <div>
            <p className="text-sm font-bold text-emerald-400">Payment recovered!</p>
            <p className="text-[10px] text-neutral-400 font-mono">$4,800.00 received from Acme Corp — Day 21</p>
          </div>
        </div>
      )}

      <button
        onClick={runSequence}
        disabled={animating}
        className={`w-full py-3 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 ${
          animating ? "bg-white/5 text-neutral-500 cursor-not-allowed"
          : "bg-accent text-black hover:bg-accent/90"
        }`}
      >
        <Activity size={14} />
        {animating ? "Sequence running..." : paid ? "▶ Replay Escalation" : "▶ Run Escalation Demo"}
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
          <p className="text-lg md:text-xl text-neutral-400 max-w-2xl mx-auto mb-6">
            The world's first industrial-grade escalation sequence for SaaS and B2B. 
            Recover up to 94% of overdue invoices automatically.
          </p>
          <div className="text-sm text-neutral-400 space-y-3 mt-6 mb-12 max-w-2xl mx-auto border border-white/5 bg-white/[0.02] p-6 rounded-xl text-left">
            <p><strong className="text-white">The Problem:</strong> Tired of chasing clients who don't pay their invoices on time?</p>
            <p><strong className="text-white">The Solution:</strong> This tool automates the sending of smart payment reminders.</p>
            <p><strong className="text-white">Who is it for:</strong> Ideal for freelancers, agencies, and project-based consultants.</p>
          </div>


          {/* LIVE DEMO */}
          <InvoiceFollowDemo />

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
              <p className="text-neutral-400 text-sm">Create invoices manually or import via CSV. Track all your clients in one place.</p>
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
              <p className="text-neutral-400 text-sm">Watch payments arrive as automated follow-ups handle the pressure for you.</p>
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
                  "Automated Email Sequences",
                  "AI-Powered Debt Risk Profiling",
                  "Debtor Risk Semaphore",
                  "Escalation Tone Automation",
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
            <p><strong>Reembolsos:</strong> Tienes un trial gratuito de 7 días. Una vez procesado el cargo mensual de $9.99, todas las ventas son definitivas y no se emiten reembolsos.</p>
          </div>
          <p className="mt-4">&copy; 2024 InvoiceFollow. Part of the DevForge ecosystem.</p>
        </div>
      </footer>
    </div>
  );
}
