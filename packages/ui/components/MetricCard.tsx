import React from "react";

interface MetricCardProps {
  label: string;
  value: React.ReactNode;
  detail?: string;
  trend?: string;
  tone?: "neutral" | "success" | "warning" | "danger" | "accent";
}

const toneColors: Record<NonNullable<MetricCardProps["tone"]>, string> = {
  neutral: "var(--color-text-secondary)",
  success: "#10B981",
  warning: "#F59E0B",
  danger: "#EF4444",
  accent: "var(--color-accent)",
};

export function MetricCard({ label, value, detail, trend, tone = "accent" }: MetricCardProps) {
  return (
    <div className="surface-card-raised border border-white/10 p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>
          {label}
        </p>
        {trend ? (
          <span className="rounded-md px-2 py-1 text-xs font-semibold" style={{ color: toneColors[tone], backgroundColor: "rgba(255,255,255,0.04)" }}>
            {trend}
          </span>
        ) : null}
      </div>
      <div className="mt-3 text-2xl font-bold tracking-normal" style={{ color: "var(--color-text)" }}>
        {value}
      </div>
      {detail ? (
        <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
          {detail}
        </p>
      ) : null}
    </div>
  );
}
