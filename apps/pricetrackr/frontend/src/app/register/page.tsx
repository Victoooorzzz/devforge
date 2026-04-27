"use client";
import { useState, Suspense } from "react";
import { auth, trackEvent } from "@devforge/core";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

function RegisterForm() {
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [plan, setPlan] = useState(searchParams.get("plan") || "starter");
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
        plan,
        trial: plan === "starter"
      });

      if (success) {
        trackEvent("user_signup", { plan, trial: plan === "starter" });
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
            Price<span className="text-accent">Trackr</span>
          </Link>
          <p className="text-sm text-neutral-400">Start your 14-day free trial</p>
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

          <div className="pt-2">
            <label className="block text-xs font-medium text-neutral-400 mb-2 uppercase tracking-wider">Selected Plan</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setPlan("starter")}
                className={`text-xs py-2 px-3 rounded-lg border transition-all ${
                  plan === "starter" 
                    ? "border-accent bg-accent/10 text-white" 
                    : "border-white/5 bg-white/5 text-neutral-400 hover:bg-white/10"
                }`}
              >
                Starter (Free Trial)
              </button>
              <button
                type="button"
                onClick={() => setPlan("pro")}
                className={`text-xs py-2 px-3 rounded-lg border transition-all ${
                  plan === "pro" 
                    ? "border-accent bg-accent/10 text-white" 
                    : "border-white/5 bg-white/5 text-neutral-400 hover:bg-white/10"
                }`}
              >
                Pro ($19/mo)
              </button>
            </div>
          </div>

          {error && <p className="text-red-500 text-xs text-center">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-3 mt-4"
          >
            {loading ? "Creating account..." : "Start Free Trial"}
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
