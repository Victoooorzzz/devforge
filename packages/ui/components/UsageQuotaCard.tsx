interface UsageQuotaCardProps {
  label: string;
  used: number;
  limit: number;
  unit?: string;
  caption?: string;
  tone?: "accent" | "warning" | "danger";
}

const toneColor: Record<NonNullable<UsageQuotaCardProps["tone"]>, string> = {
  accent: "var(--color-accent)",
  warning: "#F59E0B",
  danger: "#EF4444",
};

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

export function UsageQuotaCard({ label, used, limit, unit = "", caption, tone = "accent" }: UsageQuotaCardProps) {
  const percentage = limit <= 0 ? 0 : Math.min(100, Math.round((used / limit) * 100));
  const color = toneColor[tone];

  return (
    <div className="dashboard-card-motion surface-card-raised border border-white/10 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>
          {label}
        </p>
        <span className="text-xs font-semibold" style={{ color }}>
          {percentage}%
        </span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-md bg-white/10">
        <div className="dashboard-progress-bar h-full rounded-md" style={{ width: `${percentage}%`, backgroundColor: color }} />
      </div>
      <div className="mt-3 flex items-center justify-between gap-3 text-sm">
        <span style={{ color: "var(--color-text)" }}>
          {formatNumber(used)}{unit}
        </span>
        <span style={{ color: "var(--color-text-secondary)" }}>
          of {formatNumber(limit)}{unit}
        </span>
      </div>
      {caption ? (
        <p className="mt-2 text-xs leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
          {caption}
        </p>
      ) : null}
    </div>
  );
}
