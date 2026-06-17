"use client";

import React from "react";

type ToastTone = "success" | "error" | "info";

export interface DashboardToast {
  tone: ToastTone;
  message: string;
}

const toastStyles: Record<ToastTone, { border: string; text: string; bg: string }> = {
  success: {
    border: "rgba(16,185,129,0.35)",
    text: "#10B981",
    bg: "rgba(16,185,129,0.12)",
  },
  error: {
    border: "rgba(239,68,68,0.35)",
    text: "#EF4444",
    bg: "rgba(239,68,68,0.12)",
  },
  info: {
    border: "var(--color-border)",
    text: "var(--color-text)",
    bg: "var(--color-surface-raised)",
  },
};

interface ActionToastProps {
  toast: DashboardToast | null;
  onDismiss: () => void;
}

export function ActionToast({ toast, onDismiss }: ActionToastProps) {
  if (!toast) return null;
  const styles = toastStyles[toast.tone];

  return (
    <div
      className="fixed right-4 top-4 z-50 flex max-w-sm items-start gap-3 rounded-lg px-4 py-3 text-sm shadow-2xl"
      style={{
        backgroundColor: styles.bg,
        border: `1px solid ${styles.border}`,
        color: styles.text,
      }}
      role={toast.tone === "error" ? "alert" : "status"}
    >
      <span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: styles.text }} />
      <p className="flex-1 leading-5">{toast.message}</p>
      <button
        type="button"
        onClick={onDismiss}
        className="rounded px-1 text-xs opacity-70 transition hover:opacity-100"
        aria-label="Dismiss message"
      >
        Close
      </button>
    </div>
  );
}

interface DashboardEmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  actionLabel: string;
  onAction: () => void;
}

export function DashboardEmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
}: DashboardEmptyStateProps) {
  return (
    <div
      className="flex flex-col items-center justify-center rounded-lg px-6 py-14 text-center"
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px dashed var(--color-border)",
      }}
    >
      <div
        className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg"
        style={{ backgroundColor: "var(--color-accent-dim)", color: "var(--color-accent)" }}
      >
        {icon}
      </div>
      <h2 className="mb-2 text-base font-semibold" style={{ color: "var(--color-text)" }}>
        {title}
      </h2>
      <p className="mb-5 max-w-md text-sm leading-6" style={{ color: "var(--color-text-secondary)" }}>
        {description}
      </p>
      <button type="button" onClick={onAction} className="btn-primary">
        {actionLabel}
      </button>
    </div>
  );
}

interface WelcomeStepsProps {
  title: string;
  description: string;
  steps: string[];
  actionLabel: string;
  onAction: () => void;
}

export function WelcomeSteps({
  title,
  description,
  steps,
  actionLabel,
  onAction,
}: WelcomeStepsProps) {
  return (
    <section
      className="mb-6 rounded-lg p-5"
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
      }}
    >
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--color-accent)" }}>
            First run
          </p>
          <h2 className="mb-2 text-lg font-semibold" style={{ color: "var(--color-text)" }}>
            {title}
          </h2>
          <p className="max-w-xl text-sm leading-6" style={{ color: "var(--color-text-secondary)" }}>
            {description}
          </p>
        </div>
        <button type="button" onClick={onAction} className="btn-primary shrink-0">
          {actionLabel}
        </button>
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-3">
        {steps.map((step, index) => (
          <div
            key={step}
            className="rounded-lg p-3"
            style={{ backgroundColor: "var(--color-surface-raised)" }}
          >
            <span className="mb-2 inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold"
              style={{ backgroundColor: "var(--color-accent-dim)", color: "var(--color-accent)" }}>
              {index + 1}
            </span>
            <p className="text-sm leading-5" style={{ color: "var(--color-text)" }}>
              {step}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

interface InlineErrorStateProps {
  title: string;
  description: string;
  onRetry: () => void;
  supportHref?: string;
}

export function InlineErrorState({
  title,
  description,
  onRetry,
  supportHref = "mailto:support@devforgeapp.pro",
}: InlineErrorStateProps) {
  return (
    <div
      className="rounded-lg p-5"
      style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)" }}
      role="alert"
    >
      <h2 className="mb-2 text-base font-semibold" style={{ color: "#EF4444" }}>
        {title}
      </h2>
      <p className="mb-4 text-sm leading-6" style={{ color: "var(--color-text-secondary)" }}>
        {description}
      </p>
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={onRetry} className="btn-secondary">
          Retry
        </button>
        <a href={supportHref} className="btn-ghost">
          Contact support
        </a>
      </div>
    </div>
  );
}

export function InlineSpinner() {
  return (
    <span
      className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
      aria-hidden="true"
    />
  );
}

export function DashboardSkeleton({ rows = 4, metrics = 4 }: { rows?: number; metrics?: number }) {
  return (
    <div className="space-y-6" aria-label="Loading dashboard">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {Array.from({ length: metrics }).map((_, index) => (
          <div key={index} className="rounded-lg p-4" style={{ backgroundColor: "var(--color-surface)" }}>
            <div className="mb-3 h-3 w-20 animate-pulse rounded bg-white/10" />
            <div className="h-6 w-24 animate-pulse rounded bg-white/15" />
          </div>
        ))}
      </div>
      <div className="rounded-lg p-4" style={{ backgroundColor: "var(--color-surface)" }}>
        {Array.from({ length: rows }).map((_, index) => (
          <div
            key={index}
            className="flex items-center gap-4 border-b border-white/5 py-4 last:border-b-0"
          >
            <div className="h-10 w-10 animate-pulse rounded-lg bg-white/10" />
            <div className="min-w-0 flex-1">
              <div className="mb-2 h-3 w-2/5 animate-pulse rounded bg-white/15" />
              <div className="h-3 w-3/5 animate-pulse rounded bg-white/10" />
            </div>
            <div className="h-8 w-24 animate-pulse rounded bg-white/10" />
          </div>
        ))}
      </div>
    </div>
  );
}
