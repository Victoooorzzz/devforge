// apps/template/frontend/src/app/login/page.tsx
"use client";

import { useState } from "react";
import { apiClient, setToken, trackEvent } from "@devforge/core";
import { product } from "@/config/product";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const { data } = await apiClient.post<{ access_token: string }>("/auth/login", {
        email,
        password,
      });
      setToken(data.access_token);
      trackEvent("trial_started");
      window.location.href = "/dashboard";
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setError(apiErr.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center px-6"
      style={{ backgroundColor: "var(--color-bg)" }}
    >
      <div className="w-full max-w-sm">
        <h1
          className="text-2xl font-bold tracking-tight text-center mb-2"
          style={{ color: "var(--color-text)" }}
        >
          Log in to {product.name}
        </h1>
        <p
          className="text-sm text-center mb-8"
          style={{ color: "var(--color-text-secondary)" }}
        >
          Enter your credentials to continue
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="login-email"
              className="block text-xs font-medium mb-1.5"
              style={{ color: "var(--color-text-secondary)" }}
            >
              Email
            </label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-field"
              required
            />
          </div>

          <div>
            <label
              htmlFor="login-password"
              className="block text-xs font-medium mb-1.5"
              style={{ color: "var(--color-text-secondary)" }}
            >
              Password
            </label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field"
              required
            />
          </div>

          {error && (
            <p className="text-xs" style={{ color: "#EF4444" }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-3 disabled:opacity-50"
          >
            {loading ? "Logging in..." : "Log in"}
          </button>
        </form>

        <p
          className="text-sm text-center mt-6"
          style={{ color: "var(--color-text-secondary)" }}
        >
          No account?{" "}
          <a
            href="/register"
            className="font-medium"
            style={{ color: "var(--color-accent)" }}
          >
            Sign up
          </a>
        </p>
      </div>
    </div>
  );
}
