import React from "react";

export type StatusBadgeTone = "neutral" | "success" | "warning" | "danger" | "accent" | "locked";

interface StatusBadgeProps {
  children: React.ReactNode;
  tone?: StatusBadgeTone;
  className?: string;
}

const toneStyles: Record<StatusBadgeTone, { color: string; backgroundColor: string; borderColor: string }> = {
  neutral: { color: "var(--color-text-secondary)", backgroundColor: "rgba(163,163,163,0.1)", borderColor: "rgba(163,163,163,0.18)" },
  success: { color: "#10B981", backgroundColor: "rgba(16,185,129,0.1)", borderColor: "rgba(16,185,129,0.2)" },
  warning: { color: "#F59E0B", backgroundColor: "rgba(245,158,11,0.1)", borderColor: "rgba(245,158,11,0.2)" },
  danger: { color: "#EF4444", backgroundColor: "rgba(239,68,68,0.1)", borderColor: "rgba(239,68,68,0.2)" },
  accent: { color: "var(--color-accent)", backgroundColor: "var(--color-accent-dim)", borderColor: "color-mix(in srgb, var(--color-accent) 32%, transparent)" },
  locked: { color: "#A3A3A3", backgroundColor: "rgba(255,255,255,0.06)", borderColor: "rgba(255,255,255,0.1)" },
};

export function StatusBadge({ children, tone = "neutral", className = "" }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-semibold ${className}`}
      style={toneStyles[tone]}
    >
      {children}
    </span>
  );
}
