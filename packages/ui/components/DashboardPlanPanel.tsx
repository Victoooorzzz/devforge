import type { DevForgeProduct, PlanSlug } from "@devforge/core";
import { IntegrationCard } from "./IntegrationCard";
import { StatusBadge } from "./StatusBadge";
import { UpgradePrompt } from "./UpgradePrompt";
import { UsageQuotaCard } from "./UsageQuotaCard";

export interface DashboardQuota {
  label: string;
  used: number;
  limit: number;
  unit?: string;
  caption?: string;
}

interface DashboardPlanPanelProps {
  product: DevForgeProduct;
  plan?: PlanSlug;
  quotas?: DashboardQuota[];
  lockedFeatures?: string[];
}

const defaultQuotaByProduct: Record<DevForgeProduct["slug"], DashboardQuota[]> = {
  filecleaner: [
    { label: "File size", used: 4, limit: 10, unit: " MB", caption: "Free max upload before Pro." },
    { label: "Retention", used: 1, limit: 1, unit: " day", caption: "Pro keeps files for 2 days; Team keeps them for 7." },
  ],
  webhookmonitor: [
    { label: "Events today", used: 38, limit: 100, caption: "Free daily event quota." },
    { label: "Endpoints", used: 1, limit: 1, caption: "Pro unlocks 10 endpoints." },
  ],
  feedbacklens: [
    { label: "Feedback this month", used: 42, limit: 100, caption: "Free monthly analysis quota." },
    { label: "Sources", used: 2, limit: 2, caption: "Pro adds GitHub, Canny, Twitter, and Reddit." },
  ],
  pricetrackr: [
    { label: "Active trackers", used: 2, limit: 5, caption: "Pro supports 100 trackers." },
    { label: "Check frequency", used: 24, limit: 24, unit: " h", caption: "Pro checks hourly; Team can check every 10 minutes." },
  ],
  invoicefollow: [
    { label: "Active invoices", used: 3, limit: 5, caption: "Pro supports 50 active invoices." },
    { label: "Emails this month", used: 12, limit: 25, caption: "Free monthly reminder quota." },
    { label: "NLP analyses", used: 4, limit: 10, caption: "Reply classification quota." },
  ],
};

const defaultLockedByProduct: Record<DevForgeProduct["slug"], string[]> = {
  filecleaner: ["Schema validation", "Anomaly detection", "10k fuzzy matching", "Parallel batch"],
  webhookmonitor: ["Replay", "Payload diff", "Advanced search", "Longer retention"],
  feedbacklens: ["GitHub issue creation", "Weekly digest", "More sources", "365-day history"],
  pricetrackr: ["Hourly checks", "Webhook alerts", "Custom selectors at scale", "10-minute team checks"],
  invoicefollow: ["Gmail sync", "Stripe/PayPal reconciliation", "Weekly digest", "API access"],
};

export function DashboardPlanPanel({
  product,
  plan = "free",
  quotas,
  lockedFeatures,
}: DashboardPlanPanelProps) {
  const activeQuotas = quotas && quotas.length ? quotas : defaultQuotaByProduct[product.slug];
  const activeLocked = lockedFeatures && lockedFeatures.length ? lockedFeatures : defaultLockedByProduct[product.slug];
  const proPlan = product.plans.find((item) => item.slug === "pro");
  const teamPlan = product.plans.find((item) => item.slug === "team");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>
            Plan and usage
          </p>
          <h2 className="mt-1 text-xl font-semibold" style={{ color: "var(--color-text)" }}>
            {product.name} {plan.toUpperCase()} workspace
          </h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusBadge tone={plan === "free" ? "neutral" : plan === "pro" ? "accent" : "success"}>{plan}</StatusBadge>
          <StatusBadge tone="accent">{proPlan?.priceLabel || "$9.99"} Pro</StatusBadge>
          <StatusBadge tone="success">{teamPlan?.priceLabel || "$49"} Team</StatusBadge>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {activeQuotas.map((quota) => (
          <UsageQuotaCard key={quota.label} {...quota} tone={quota.used >= quota.limit ? "warning" : "accent"} />
        ))}
      </div>

      {plan === "free" ? (
        <UpgradePrompt
          title="Advanced workflow is plan-gated"
          description="The dashboard exposes the same upgrade gates enforced by the backend limits. Upgrade when you need higher volume, longer retention, or automation features."
          ctaHref="/register?plan=pro"
          ctaLabel="Upgrade to Pro"
          features={activeLocked.slice(0, 4)}
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {activeLocked.slice(0, 4).map((feature) => (
            <IntegrationCard key={feature} name={feature} description="Available based on your current paid plan and backend limits." status="Unlocked" tone="success" />
          ))}
        </div>
      )}
    </div>
  );
}
