"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { auth, trackEvent } from "@devforge/core";
import { useRouter, useSearchParams } from "next/navigation";

type PlanSlug = "free" | "pro" | "team";

const planOptions: Array<{ slug: PlanSlug; label: string; detail: string }> = [
  { slug: "free", label: "Free", detail: "$0" },
  { slug: "pro", label: "Pro", detail: "$19/mo" },
  { slug: "team", label: "Team", detail: "$79/mo" },
];

function normalizePlan(value: string | null): PlanSlug {
  return value === "free" || value === "team" ? value : "pro";
}

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [plan, setPlan] = useState<PlanSlug>(() => normalizePlan(searchParams.get("plan")));
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { success, error: authError, isEmailVerified, checkoutUrl } = await auth.register({
        name,
        email,
        password,
        app_name: "feedbacklens",
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
      setError("Could not create account. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-8" style={{ backgroundColor: "var(--color-bg)" }}>
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Link href="/" className="text-2xl font-bold" style={{ color: "var(--color-accent)" }}>
            FeedbackLens
          </Link>
          <p className="text-sm mt-2" style={{ color: "var(--color-text-secondary)" }}>
            {plan === "free" ? "Create your free workspace" : `Start ${planOptions.find((item) => item.slug === plan)?.label} checkout`}
          </p>
        </div>

        <div className="badge mb-6 w-full justify-center text-center py-2 rounded-md" style={{ backgroundColor: "var(--color-accent-dim)", color: "var(--color-accent)" }}>
          Free $0 | Pro $19/month | Team $79/month
        </div>

        <div className="surface-card p-8 rounded-lg" style={{ border: "1px solid var(--color-border)" }}>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--color-text)" }}>
                Name
              </label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="input-field" placeholder="Your name" required autoComplete="name" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--color-text)" }}>
                Email
              </label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="input-field" placeholder="you@example.com" required autoComplete="email" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--color-text)" }}>
                Password
              </label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="input-field" placeholder="At least 8 characters" required minLength={8} autoComplete="new-password" />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2" style={{ color: "var(--color-text)" }}>
                Plan
              </label>
              <div className="grid grid-cols-3 gap-2">
                {planOptions.map((option) => (
                  <button
                    key={option.slug}
                    type="button"
                    onClick={() => setPlan(option.slug)}
                    className="rounded-md border px-3 py-2 text-left text-xs transition"
                    style={{
                      borderColor: plan === option.slug ? "var(--color-accent)" : "var(--color-border)",
                      backgroundColor: plan === option.slug ? "var(--color-accent-dim)" : "rgba(255,255,255,0.04)",
                      color: plan === option.slug ? "var(--color-text)" : "var(--color-text-secondary)",
                    }}
                  >
                    <span className="block font-semibold">{option.label}</span>
                    <span>{option.detail}</span>
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <div className="text-sm px-3 py-2 rounded-md" style={{ backgroundColor: "rgba(239,68,68,0.1)", color: "#EF4444" }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full justify-center mt-2 disabled:opacity-60">
              {loading ? "Creating account..." : plan === "free" ? "Create Free Account" : `Continue with ${plan}`}
            </button>
          </form>
        </div>

        <p className="text-center text-xs mt-4" style={{ color: "var(--color-text-secondary)" }}>
          By registering, you agree to our Terms of Service.
        </p>
        <p className="text-center text-sm mt-3" style={{ color: "var(--color-text-secondary)" }}>
          Already have an account?{" "}
          <Link href="/login" style={{ color: "var(--color-accent)" }} className="font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-black flex items-center justify-center"><p style={{ color: "var(--color-text-secondary)" }}>Loading...</p></div>}>
      <RegisterForm />
    </Suspense>
  );
}
