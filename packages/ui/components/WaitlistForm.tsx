// packages/ui/components/WaitlistForm.tsx
"use client";

import React, { useState } from "react";

interface WaitlistFormProps {
  placeholder?: string;
  buttonText?: string;
  onSubmit: (email: string) => Promise<void>;
  successMessage?: string;
}

export function WaitlistForm({
  placeholder = "Enter your email",
  buttonText = "Join Waitlist",
  onSubmit,
  successMessage = "You're on the list!",
}: WaitlistFormProps) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setStatus("loading");
    setErrorMessage("");

    try {
      await onSubmit(email);
      setStatus("success");
      setEmail("");
    } catch (err) {
      setStatus("error");
      setErrorMessage(err instanceof Error ? err.message : "Something went wrong");
    }
  };

  if (status === "success") {
    return (
      <div
        className="flex items-center gap-3 p-4 rounded-lg animate-scale-in"
        style={{
          backgroundColor: "var(--color-accent-dim)",
          color: "var(--color-accent)",
        }}
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path
            d="M16.7 5.3L7.5 14.5L3.3 10.3"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span className="text-sm font-medium">{successMessage}</span>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-md">
      <div className="flex gap-3">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={placeholder}
          required
          className="input-field flex-1"
          disabled={status === "loading"}
        />
        <button
          type="submit"
          disabled={status === "loading"}
          className="btn-primary whitespace-nowrap disabled:opacity-50"
        >
          {status === "loading" ? (
            <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            buttonText
          )}
        </button>
      </div>
      {status === "error" && (
        <p className="text-xs mt-2" style={{ color: "#EF4444" }}>
          {errorMessage}
        </p>
      )}
    </form>
  );
}
