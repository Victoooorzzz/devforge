import { StatusBadge, type StatusBadgeTone } from "./StatusBadge";

export interface ActivityTimelineItem {
  time: string;
  title: string;
  description: string;
  status?: string;
  tone?: StatusBadgeTone;
}

interface ActivityTimelineProps {
  items: ActivityTimelineItem[];
}

export function ActivityTimeline({ items }: ActivityTimelineProps) {
  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div key={`${item.time}-${item.title}`} className="grid grid-cols-[80px_1fr] gap-3">
          <div className="pt-1 text-xs font-mono" style={{ color: "var(--color-text-secondary)" }}>
            {item.time}
          </div>
          <div className="relative border-l border-white/10 pl-4">
            <span className="absolute -left-[5px] top-2 h-2.5 w-2.5 rounded-full" style={{ backgroundColor: index === 0 ? "var(--color-accent)" : "var(--color-surface-bright)" }} />
            <div className="surface-card-raised border border-white/10 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h4 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>
                  {item.title}
                </h4>
                {item.status ? <StatusBadge tone={item.tone || "neutral"}>{item.status}</StatusBadge> : null}
              </div>
              <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                {item.description}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
