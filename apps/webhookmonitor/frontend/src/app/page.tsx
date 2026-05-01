"use client";
import Link from "next/link";
import { Check, Zap, Eye, ShieldCheck } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-accent selection:text-black">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 glass border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <img src="/devforge-logo-white.svg" alt="DevForge" className="h-6 w-auto" />
            <span className="text-xl font-bold tracking-tighter border-l border-white/20 pl-3">
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
      <section className="pt-32 pb-20 px-6 min-h-[85vh] flex flex-col justify-center">
        <div className="max-w-6xl mx-auto w-full grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 text-accent text-xs font-mono mb-6 uppercase tracking-widest">
              <Eye size={14} />
              <span>Developer-First Webhook Debugging</span>
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-b from-white to-white/50 bg-clip-text text-transparent">
              Intercept & Inspect.
            </h1>
            <p className="text-lg text-neutral-400 mb-10 font-mono text-sm leading-relaxed">
              Stop guessing why your integrations are failing. Monitor incoming requests in real-time, inspect payloads, and replay webhooks to debug your local environment.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link href="/register" className="btn-primary px-8 py-4 text-sm font-mono text-center">
                Initialize System
              </Link>
            </div>
          </div>
          
          {/* Terminal UI */}
          <div className="relative w-full rounded-lg overflow-hidden bg-[#0A0A0A] border border-[#282627] shadow-2xl font-mono text-xs">
            {/* Terminal Header */}
            <div className="h-8 bg-[#191718] border-b border-[#282627] flex items-center px-4 gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-red-500/80"></div>
              <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80"></div>
              <div className="w-2.5 h-2.5 rounded-full bg-green-500/80"></div>
              <span className="ml-4 text-[#7F7A7C]">webhook-monitor-stream</span>
            </div>
            
            {/* Terminal Body */}
            <div className="p-4 flex flex-col gap-3 min-h-[300px]">
              <div className="flex items-start gap-3">
                <span className="text-[#7F7A7C]">14:02:11</span>
                <span className="text-[#10B981]">POST</span>
                <span className="text-white">/api/webhooks/stripe</span>
                <span className="text-[#10B981] ml-auto">200 OK</span>
              </div>
              <div className="pl-16 text-[#7F7A7C] whitespace-pre">
                {"{\n  \"type\": \"payment_intent.succeeded\",\n  \"data\": {\n    \"object\": {\n      \"id\": \"pi_3Mtw...\",\n      \"amount\": 999\n    }\n  }\n}"}
              </div>
              
              <div className="flex items-start gap-3 mt-2">
                <span className="text-[#7F7A7C]">14:02:15</span>
                <span className="text-[#10B981]">POST</span>
                <span className="text-white">/api/webhooks/github</span>
                <span className="text-[#EF4444] ml-auto">401 ERR</span>
              </div>
              <div className="pl-16 text-[#EF4444]/80">
                Error: Signature verification failed
              </div>

              <div className="flex items-start gap-3 mt-4">
                <span className="text-[#7F7A7C]">Listening for incoming webhooks...</span>
                <div className="w-2 h-4 bg-[#821346] animate-pulse"></div>
              </div>
            </div>
            
            {/* Glow Effect */}
            <div className="absolute inset-0 bg-[#821346]/5 pointer-events-none"></div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-6 border-t border-white/5">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="glass p-8 rounded-2xl border border-white/5">
              <Eye className="text-accent mb-4" size={32} />
              <h3 className="text-xl font-bold mb-3">Live Monitoring</h3>
              <p className="text-neutral-400 text-sm leading-relaxed">
                Watch webhooks arrive in real-time with full headers and body inspection. No more digging through logs.
              </p>
            </div>
            <div className="glass p-8 rounded-2xl border border-white/5">
              <Zap className="text-accent mb-4" size={32} />
              <h3 className="text-xl font-bold mb-3">Instant Replay</h3>
              <p className="text-neutral-400 text-sm leading-relaxed">
                Resend any received webhook to your local server or another endpoint with a single click to test your logic.
              </p>
            </div>
            <div className="glass p-8 rounded-2xl border border-white/5">
              <ShieldCheck className="text-accent mb-4" size={32} />
              <h3 className="text-xl font-bold mb-3">Security Logging</h3>
              <p className="text-neutral-400 text-sm leading-relaxed">
                Track security signatures and verify payloads from providers like Stripe, GitHub, and Shopify automatically.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 px-6 border-t border-white/5 bg-white/[0.02]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Pricing built for developers.</h2>
            <p className="text-neutral-400">Everything you need to ship stable integrations.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Starter */}
            <div className="glass p-10 rounded-3xl border border-white/10 flex flex-col">
              <div className="mb-8">
                <h3 className="text-xl font-bold mb-2">Starter</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-bold">$9.99</span>
                  <span className="text-neutral-400">/mo</span>
                </div>
                <p className="text-sm text-neutral-400 mt-4">Perfect for individual developers and side projects.</p>
              </div>
              <ul className="space-y-4 mb-10 flex-1">
                {["100,000 Requests/mo", "7-Day Retention", "Basic Replay", "1 Endpoint", "Standard Support"].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-sm text-neutral-300">
                    <Check size={16} className="text-accent" /> {item}
                  </li>
                ))}
              </ul>
              <Link href="/register?plan=starter" className="btn-primary py-4 text-center">
                Start 7-Day Free Trial
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
                  <span className="text-4xl font-bold">$9.99</span>
                  <span className="text-neutral-400">/mo</span>
                </div>
                <p className="text-sm text-neutral-400 mt-4">Advanced monitoring for professional software teams.</p>
              </div>
              <ul className="space-y-4 mb-10 flex-1">
                {["Unlimited Requests", "90-Day Retention", "Advanced Replay Scripts", "Unlimited Endpoints", "Team Collaboration", "Priority Support"].map((item) => (
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
        <p>&copy; 2024 WebhookMonitor. Part of the DevForge ecosystem.</p>
      </footer>
    </div>
  );
}
