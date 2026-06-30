import type { DevForgeProduct, PlanSlug } from "@devforge/core";
import { StatusBadge, type StatusBadgeTone } from "./StatusBadge";

interface PricingTableProps {
  product: DevForgeProduct;
  currentPlan?: PlanSlug;
  compact?: boolean;
}

const planAccent: Record<PlanSlug, StatusBadgeTone> = {
  free: "neutral",
  pro: "accent",
  team: "success",
};

export function PricingTable({ product, currentPlan, compact = false }: PricingTableProps) {
  return (
    <div className={`grid gap-4 ${compact ? "md:grid-cols-3" : "lg:grid-cols-3"}`}>
      {product.plans.map((plan) => {
        const isCurrent = currentPlan === plan.slug;
        const href = plan.slug === "free" ? "/register?plan=free" : `/register?plan=${plan.slug}`;
        return (
          <div
            key={plan.slug}
            className={`surface-card-raised flex flex-col border p-5 ${plan.slug === "pro" ? "border-[color:var(--color-accent)]" : "border-white/10"}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold" style={{ color: "var(--color-text)" }}>
                  {plan.name}
                </h3>
                <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                  {plan.description}
                </p>
              </div>
              {isCurrent ? <StatusBadge tone="success">Current</StatusBadge> : <StatusBadge tone={planAccent[plan.slug]}>{plan.slug === "pro" ? "Best fit" : plan.name}</StatusBadge>}
            </div>

            <div className="mt-6">
              <span className="text-4xl font-bold tracking-normal" style={{ color: "var(--color-text)" }}>
                {plan.priceLabel}
              </span>
              {plan.price > 0 ? (
                <span className="ml-2 text-sm" style={{ color: "var(--color-text-secondary)" }}>
                  /mo
                </span>
              ) : null}
            </div>

            <ul className="mt-5 flex-1 space-y-2">
              {plan.limits.map((limit) => (
                <li key={limit} className="flex gap-2 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: "var(--color-accent)" }} />
                  <span>{limit}</span>
                </li>
              ))}
            </ul>

            <a href={href} className={`mt-6 w-full ${plan.slug === "pro" ? "btn-primary" : "btn-secondary"}`}>
              {plan.cta}
            </a>
          </div>
        );
      })}
    </div>
  );
}
