"use client";

import { Suspense, useState } from "react";
import { auth, trackEvent } from "@devforge/core";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

type PlanSlug = "free" | "pro" | "team";

const planOptions: Array<{ slug: PlanSlug; label: string; detail: string }> = [
  { slug: "free", label: "Free", detail: "$0" },
  { slug: "pro", label: "Pro", detail: "$9.99/mo" },
  { slug: "team", label: "Team", detail: "$49/mo" },
];

function normalizePlan(value: string | null): PlanSlug {
  return value === "free" || value === "team" ? value : "pro";
}

function RegisterForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [plan, setPlan] = useState<PlanSlug>(() => normalizePlan(searchParams.get("plan")));
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const { success, error: authError, isEmailVerified, checkoutUrl } = await auth.register({
        name,
        email,
        password,
        app_name: "invoicefollow",
        plan,
        trial: plan !== "free",
      });

      if (success) {
        trackEvent("user_signup", { plan, trial: plan !== "free" });

        if (checkoutUrl) {
          window.location.href = checkoutUrl;
          return;
        }

        if (isEmailVerified === false) {
          router.push("/verify");
          return;
        }

        router.push("/dashboard");
      } else {
        setError(authError || "Registration failed");
      }
    } catch {
      setError("An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black p-4">
      <div className="glass w-full max-w-md p-8 rounded-lg border border-white/5">
        <div className="mb-8 text-center">
          <Link href="/" className="text-2xl font-bold tracking-tighter mb-2 inline-block">
            Invoice<span className="text-accent">Follow</span>
          </Link>
          <p className="text-sm text-neutral-400">{plan === "free" ? "Create your free workspace" : `Start ${planOptions.find((item) => item.slug === plan)?.label} checkout`}</p>
        </div>

        <form onSubmit={handleRegister} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-neutral-400 mb-1.5 uppercase tracking-wider">Name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="input-field" placeholder="Your name" required autoComplete="name" />
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-400 mb-1.5 uppercase tracking-wider">Email Address</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="input-field" placeholder="name@example.com" required autoComplete="email" />
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-400 mb-1.5 uppercase tracking-wider">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="input-field" placeholder="At least 8 characters" required minLength={8} autoComplete="new-password" />
          </div>

          <div>
            <label className="block text-xs font-medium text-neutral-400 mb-2 uppercase tracking-wider">Plan</label>
            <div className="grid grid-cols-3 gap-2">
              {planOptions.map((option) => (
                <button
                  key={option.slug}
                  type="button"
                  onClick={() => setPlan(option.slug)}
                  className={`rounded-md border px-3 py-2 text-left text-xs transition ${plan === option.slug ? "border-accent bg-accent/10 text-white" : "border-white/10 bg-white/5 text-neutral-400"}`}
                >
                  <span className="block font-semibold">{option.label}</span>
                  <span>{option.detail}</span>
                </button>
              ))}
            </div>
          </div>

          {error && <p className="text-red-500 text-xs text-center">{error}</p>}

          <button type="submit" disabled={loading} className="btn-primary w-full py-4 mt-4 text-sm font-bold uppercase tracking-wider">
            {loading ? "Creating account..." : plan === "free" ? "Create Free Account" : `Continue with ${plan}`}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-neutral-400">
          Already have an account? <Link href="/login" className="text-accent hover:underline">Login here</Link>
        </p>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-black flex items-center justify-center"><p className="text-neutral-400">Loading...</p></div>}>
      <RegisterForm />
    </Suspense>
  );
}
