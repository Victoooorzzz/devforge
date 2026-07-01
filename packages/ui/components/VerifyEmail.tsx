"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { verify } from "@devforge/core";

const API_BASE = typeof window !== "undefined"
  ? (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  : (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000");

export function VerifyEmail({ onVerified }: { onVerified?: () => void }) {
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resending, setResending] = useState(false);
  const [resendDone, setResendDone] = useState(false);
  const router = useRouter();

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (code.length !== 6) {
      setError("El codigo debe ser de 6 digitos");
      return;
    }

    setLoading(true);
    setError(null);

    const result = await verify(code);

    if (result.success) {
      if (onVerified) {
        onVerified();
      } else {
        router.push("/dashboard");
      }
    } else {
      setError(result.error || "Codigo invalido");
    }
    setLoading(false);
  };

  const handleResend = async () => {
    setResending(true);
    setResendDone(false);
    setError(null);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("devforge_token") : null;
      await fetch(`${API_BASE}/auth/resend-code`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: "include",
      });
      setResendDone(true);
    } catch {
      setError("No se pudo reenviar el codigo. Intenta de nuevo.");
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4">
      <div className="surface-card-raised w-full max-w-md border border-white/10 p-6 shadow-2xl sm:p-8">
        <div className="mb-8 text-center">
          <div
            className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-lg border"
            style={{
              backgroundColor: "var(--color-accent-dim)",
              borderColor: "var(--color-border)",
              color: "var(--color-accent)",
            }}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h1 className="mb-2 text-2xl font-bold sm:text-3xl" style={{ color: "var(--color-text)" }}>
            Verifica tu cuenta
          </h1>
          <p style={{ color: "var(--color-text-secondary)" }}>
            Ingresa el codigo de 6 digitos que enviamos a tu correo electronico.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="code" className="mb-2 block text-center text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
              Codigo de Verificacion
            </label>
            <input
              id="code"
              type="text"
              maxLength={6}
              placeholder="000000"
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
              className="w-full rounded-lg border border-white/10 bg-white/5 py-4 text-center font-mono text-2xl text-white placeholder-white/20 transition-all focus:outline-none focus:ring-2"
              style={{
                letterSpacing: "0.9em",
                caretColor: "var(--color-accent)",
                "--tw-ring-color": "var(--color-accent)",
              } as React.CSSProperties}
              required
              autoFocus
            />
          </div>

          {error ? (
            <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-center text-sm text-red-400">
              {error}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full justify-center py-4 font-semibold disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg className="-ml-1 mr-3 h-5 w-5 animate-spin text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Verificando...
              </span>
            ) : (
              "Confirmar Codigo"
            )}
          </button>
        </form>

        <div className="mt-8 text-center">
          <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
            No recibiste el codigo?{" "}
            <button
              type="button"
              disabled={resending}
              className="font-medium transition-colors disabled:opacity-50"
              style={{ color: "var(--color-accent)" }}
              onClick={handleResend}
            >
              {resending ? "Enviando..." : "Reenviar codigo"}
            </button>
          </p>
          {resendDone ? (
            <p className="mt-2 text-xs" style={{ color: "var(--color-accent)" }}>
              Codigo reenviado. Revisa tu correo.
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
