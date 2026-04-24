"use client";

import { useState } from "react";
import { apiClient, setToken, trackEvent } from "@devforge/core";
import { product } from "@/config/product";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { data } = await apiClient.post<{ access_token: string }>("/auth/register", { email, password });
      setToken(data.access_token);
      trackEvent("trial_started");
      window.location.href = "/dashboard";
    } catch (err: unknown) {
      setError((err as { detail?: string }).detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6" style={{ backgroundColor: "var(--color-bg)" }}>
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold tracking-tight text-center mb-2" style={{ color: "var(--color-text)" }}>Create your account</h1>
        <p className="text-sm text-center mb-8" style={{ color: "var(--color-text-secondary)" }}>Start your free trial of {product.name}</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="reg-email" className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Email</label>
            <input id="reg-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="input-field" required />
          </div>
          <div>
            <label htmlFor="reg-pw" className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Password</label>
            <input id="reg-pw" type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="input-field" minLength={8} required />
          </div>
          {error && <p className="text-xs" style={{ color: "#EF4444" }}>{error}</p>}
          <button type="submit" disabled={loading} className="btn-primary w-full py-3 disabled:opacity-50">{loading ? "Creating account..." : "Create Account"}</button>
        </form>
        <p className="text-sm text-center mt-6" style={{ color: "var(--color-text-secondary)" }}>Already have an account? <a href="/login" className="font-medium" style={{ color: "var(--color-accent)" }}>Log in</a></p>
      </div>
    </div>
  );
}
