"use client";
import { useState, Suspense } from "react";
import { auth, trackEvent, apiClient } from "@devforge/core";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { product } from "@/config/product";

function RegisterForm() {
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [plan, setPlan] = useState("pro");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const { success, error: authError } = await auth.register({
        email,
        password,
        plan: "pro",
        trial: true
      });

      if (success) {
        trackEvent("user_signup", { plan, trial: plan === "starter" });
        
        // Automatically start checkout for the Pro Trial
        try {
          const { data } = await apiClient.post("/lemonsqueezy/checkout", {
            variant_id: product.pricing.lsVariantId
          }) as { data: { checkout_url: string } };
          
          if (data.checkout_url) {
            window.location.href = data.checkout_url;
            return;
          }
        } catch (checkoutErr) {
          console.error("Failed to initiate checkout:", checkoutErr);
        }
        router.push("/dashboard");
      } else {
        setError(authError || "Registration failed");
      }
    } catch (err) {
      setError("An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black p-4">
      <div className="glass w-full max-w-md p-8 rounded-2xl border border-white/5">
        <div className="mb-8 text-center">
          <Link href="/" className="text-2xl font-bold tracking-tighter mb-2 inline-block">
            Invoice<span className="text-accent">Follow</span>
          </Link>
          <p className="text-sm text-neutral-400">Start your 7-day free trial</p>
        </div>

        <form onSubmit={handleRegister} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-neutral-400 mb-1.5 uppercase tracking-wider">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-field"
              placeholder="name@example.com"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-400 mb-1.5 uppercase tracking-wider">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field"
              placeholder="••••••••"
              required
            />
          </div>

          {/* Removido selector de plan para simplificar a Plan Unico Pro con Trial */}
          <input type="hidden" name="plan" value="pro" />

          {error && <p className="text-red-500 text-xs text-center">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-4 mt-4 text-lg font-bold uppercase tracking-wider"
          >
            {loading ? "Creating account..." : "Start 7-Day Free Trial"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-neutral-400">
          Already have an account?{" "}
          <Link href="/login" className="text-accent hover:underline">
            Login here
          </Link>
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
