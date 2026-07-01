import { StatusBadge, type StatusBadgeTone } from "./StatusBadge";

interface IntegrationCardProps {
  name: string;
  description: string;
  status?: string;
  tone?: StatusBadgeTone;
  meta?: string;
}

export function IntegrationCard({ name, description, status = "Available", tone = "accent", meta }: IntegrationCardProps) {
  return (
    <div className="dashboard-card-motion surface-card-raised border border-white/10 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>
            {name}
          </h3>
          <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
            {description}
          </p>
        </div>
        <StatusBadge tone={tone}>{status}</StatusBadge>
      </div>
      {meta ? (
        <p className="mt-4 rounded-md bg-black/30 px-3 py-2 font-mono text-xs" style={{ color: "var(--color-text-secondary)" }}>
          {meta}
        </p>
      ) : null}
    </div>
  );
}
