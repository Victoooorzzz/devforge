import React from "react";

interface UpgradePromptProps {
  title: string;
  description: string;
  ctaLabel?: string;
  ctaHref?: string;
  features?: string[];
  secondaryAction?: React.ReactNode;
}

export function UpgradePrompt({
  title,
  description,
  ctaLabel = "Upgrade",
  ctaHref = "/register?plan=pro",
  features = [],
  secondaryAction,
}: UpgradePromptProps) {
  return (
    <div className="surface-card-raised border border-white/10 p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>
            Plan limit
          </p>
          <h3 className="mt-2 text-lg font-semibold" style={{ color: "var(--color-text)" }}>
            {title}
          </h3>
          <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
            {description}
          </p>
          {features.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {features.map((feature) => (
                <span key={feature} className="rounded-md border border-white/10 bg-white/5 px-2.5 py-1 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                  {feature}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-3">
          {secondaryAction}
          <a href={ctaHref} className="btn-primary">
            {ctaLabel}
          </a>
        </div>
      </div>
    </div>
  );
}
