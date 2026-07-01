"use client";
import { useState } from "react";
import Link from "next/link";
import { setToken, apiClient } from "@devforge/core";
import { useRouter } from "next/navigation";

interface LoginResponse {
  access_token: string;
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await apiClient.post<LoginResponse>("/auth/login", { email, password });
      setToken(data.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err?.detail || "Invalid email or password");
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
            Sign in to your account
          </p>
        </div>

        {/* Form */}
        <div className="surface-card p-8 rounded-lg" style={{ border: "1px solid var(--color-border)" }}>
          <form onSubmit={handleSubmit} className="space-y-4">
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
                placeholder="••••••••"
                required
                autoComplete="current-password"
              />
            </div>

            {error && (
              <div className="text-sm px-3 py-2 rounded-md" style={{ backgroundColor: "rgba(239,68,68,0.1)", color: "#EF4444" }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full justify-center mt-2 disabled:opacity-60">
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </div>

        <p className="text-center text-sm mt-6" style={{ color: "var(--color-text-secondary)" }}>
          No account?{" "}
          <Link href="/register" style={{ color: "var(--color-accent)" }} className="font-medium">
            Start free trial
          </Link>
        </p>
      </div>
    </div>
  );
}
