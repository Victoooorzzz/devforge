"use client";
import { useState } from "react";
import { auth, trackEvent } from "@devforge/core";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const { success, error: authError, isEmailVerified } = await auth.login(email, password);
      if (success) {
        if (isEmailVerified === false) {
          router.push("/verify");
          return;
        }
        trackEvent("user_login", { method: "email" });
        router.push("/dashboard");
      } else {
        setError(authError || "Invalid credentials");
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
            File<span className="text-accent">Cleaner</span>
          </Link>
          <p className="text-sm text-neutral-400">Welcome back to your dashboard</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
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

          {error && <p className="text-red-500 text-xs text-center">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-3"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-neutral-400">
          Don't have an account?{" "}
          <Link href="/register" className="text-accent hover:underline">
            Register here
          </Link>
        </p>
      </div>
    </div>
  );
}
