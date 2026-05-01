"use client";
import { useState } from "react";
import Link from "next/link";
import { setToken, apiClient } from "@devforge/core";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { product } from "@/config/product";

interface RegisterResponse {
  access_token: string;
}

function RegisterForm() {
  const router = useRouter();
  const plan = "pro";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await apiClient.post<RegisterResponse>("/auth/register", {
        name,
        email,
        password,
        plan,
        app: "feedbacklens",
      });
      setToken(data.access_token);
      
      // Automatically start checkout for the Pro Trial
      try {
        const { data: checkoutData } = await apiClient.post("/lemonsqueezy/checkout", {
          variant_id: product.pricing.lsVariantId
        }) as { data: { checkout_url: string } };
        
        if (checkoutData.checkout_url) {
          window.location.href = checkoutData.checkout_url;
          return;
        }
      } catch (checkoutErr) {
        console.error("Failed to initiate checkout:", checkoutErr);
      }
      
      router.push("/dashboard");
    } catch (err: any) {
      setError(err?.detail || "Could not create account. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ backgroundColor: "var(--color-bg)" }}>
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="text-2xl font-bold" style={{ color: "var(--color-accent)" }}>
            FeedbackLens
          </Link>
          <p className="text-sm mt-2" style={{ color: "var(--color-text-secondary)" }}>
            Start your 7-day free Pro trial
          </p>
        </div>

        <div className="badge mb-6 w-full justify-center text-center py-2 rounded-md" style={{ backgroundColor: "var(--color-accent-dim)", color: "var(--color-accent)" }}>
          7-day free trial · Then $9.99/month · Cancel anytime
        </div>

        {/* Form */}
        <div className="surface-card p-8 rounded-lg" style={{ border: "1px solid var(--color-border)" }}>
          <form onSubmit={handleSubmit} className="space-y-4">
            <input type="hidden" name="plan" value="pro" />
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--color-text)" }}>
                Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input-field"
                placeholder="Your name"
                required
                autoComplete="name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--color-text)" }}>
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-field"
                placeholder="you@example.com"
                required
                autoComplete="email"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--color-text)" }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field"
                placeholder="At least 8 characters"
                required
                minLength={8}
                autoComplete="new-password"
              />
            </div>

            {error && (
              <div className="text-sm px-3 py-2 rounded-md" style={{ backgroundColor: "rgba(239,68,68,0.1)", color: "#EF4444" }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full justify-center mt-2 disabled:opacity-60">
              {loading ? "Creating account..." : "Start 7-Day Free Trial"}
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
    <Suspense>
      <RegisterForm />
    </Suspense>
  );
}
