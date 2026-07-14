"use client";

import { useEffect, useMemo, useState } from "react";
import { apiClient, type DevForgeProduct, type PlanSlug } from "@devforge/core";
import { IntegrationCard } from "./IntegrationCard";
import { StatusBadge } from "./StatusBadge";
import { UpgradePrompt } from "./UpgradePrompt";
import { UsageQuotaCard } from "./UsageQuotaCard";

export interface DashboardQuota {
  label: string;
  used: number;
  limit?: number;
  unit?: string;
  caption?: string;
  mode?: "usage" | "capacity";
}

interface DashboardPlanPanelProps {
  product: DevForgeProduct;
  plan?: PlanSlug;
  quotas?: DashboardQuota[];
  lockedFeatures?: string[];
}

type DashboardQuotaMeta = {
  limitKey?: string;
  unit?: string;
  caption?: string;
  mode?: "usage" | "capacity";
};

type DashboardLimitProfile = Partial<Record<
  DevForgeProduct["slug"],
  Partial<Record<PlanSlug, Record<string, number>>>
>>;

type ResolvedDashboardQuota = Required<Pick<DashboardQuota, "label" | "used" | "limit">> &
  Pick<DashboardQuota, "unit" | "caption" | "mode">;

const defaultQuotaByProduct: Record<DevForgeProduct["slug"], DashboardQuota[]> = {
  filecleaner: [
    { label: "Max upload size", used: 0 },
    { label: "Retention", used: 0 },
  ],
  webhookmonitor: [
    { label: "Events today", used: 0 },
    { label: "Endpoints", used: 0 },
    { label: "Retention", used: 0 },
  ],
  feedbacklens: [
    { label: "Feedback this month", used: 0 },
    { label: "Duplicate groups", used: 0 },
  ],
  pricetrackr: [
    { label: "Active trackers", used: 0 },
    { label: "Check frequency", used: 0 },
  ],
  invoicefollow: [
    { label: "Active invoices", used: 0 },
    { label: "Emails this month", used: 0 },
    { label: "NLP reply analyses", used: 0 },
  ],
};

const quotaMetaByProduct: Record<DevForgeProduct["slug"], Record<string, DashboardQuotaMeta>> = {
  filecleaner: {
    "File size": { limitKey: "max_upload_mb", unit: " MB", caption: "Backend-enforced upload size for this plan.", mode: "capacity" },
    "Max upload size": { limitKey: "max_upload_mb", unit: " MB", caption: "Backend-enforced upload size for this plan.", mode: "capacity" },
    Retention: { limitKey: "retention_days", unit: " days", caption: "Backend retention window for cleaned files.", mode: "capacity" },
    "Schema rules": { limitKey: "schema_max_rules", caption: "Backend schema validation rule quota." },
    "Fuzzy rows": { limitKey: "fuzzy_max_rows", caption: "Backend fuzzy matching row quota." },
  },
  webhookmonitor: {
    "Events today": { limitKey: "events_per_day", caption: "Backend daily delivery quota." },
    Endpoints: { limitKey: "max_endpoints", caption: "Backend endpoint quota." },
    Retention: { limitKey: "retention_days", unit: " days", caption: "Backend event retention window.", mode: "capacity" },
  },
  feedbacklens: {
    "Feedback this month": { limitKey: "max_feedback_per_month", caption: "Backend monthly analysis quota." },
    Sources: { limitKey: "max_sources", caption: "Backend source quota." },
    "Duplicate groups": { limitKey: "dedupe_lookback_items", caption: "Backend dedupe lookback window." },
    Retention: { limitKey: "history_retention_days", unit: " days", caption: "Backend feedback history window.", mode: "capacity" },
  },
  pricetrackr: {
    "Active trackers": { limitKey: "max_active_trackers", caption: "Backend active tracker quota." },
    "Watched links": { limitKey: "max_active_trackers", caption: "Backend watched link quota." },
    "Check frequency": { limitKey: "min_check_frequency_hours", unit: " h", caption: "Backend minimum check interval.", mode: "capacity" },
  },
  invoicefollow: {
    "Active invoices": { limitKey: "max_active_invoices", caption: "Backend active invoice quota." },
    "Emails this month": { limitKey: "monthly_emails", caption: "Backend monthly reminder quota." },
    "NLP analyses": { limitKey: "monthly_nlp", caption: "Backend reply classification quota." },
    "NLP reply analyses": { limitKey: "monthly_nlp", caption: "Backend reply classification quota." },
    Retention: { limitKey: "history_retention_days", unit: " days", caption: "Backend invoice history window.", mode: "capacity" },
  },
};

const defaultLockedByProduct: Record<DevForgeProduct["slug"], string[]> = {
  filecleaner: ["Schema validation", "Anomaly detection", "10k fuzzy matching", "Parallel batch"],
  webhookmonitor: ["Replay", "Payload diff", "Advanced search", "Longer retention"],
  feedbacklens: ["Weekly digest", "Bulk CSV import", "API import", "365-day history"],
  pricetrackr: ["Hourly checks", "Webhook alerts", "Custom selectors at scale", "10-minute team checks"],
  invoicefollow: ["Weekly digest", "API access", "Bulk import", "Longer history"],
};

interface ProfilePlanResponse {
  plans_by_product?: Partial<Record<DevForgeProduct["slug"], PlanSlug>>;
  dashboard_limits_by_product?: DashboardLimitProfile;
}

function normalizePlan(value: string | undefined): PlanSlug | null {
  return value === "free" || value === "pro" || value === "team" ? value : null;
}

function resolveQuotaLimit(
  productSlug: DevForgeProduct["slug"],
  plan: PlanSlug,
  quota: DashboardQuota,
  profileLimits: DashboardLimitProfile,
): ResolvedDashboardQuota {
  const meta = quotaMetaByProduct[productSlug]?.[quota.label] || {};
  const limitKey = meta.limitKey;
  const profileValue = limitKey ? profileLimits[productSlug]?.[plan]?.[limitKey] : undefined;
  const rawLimit = typeof profileValue === "number" ? profileValue : quota.limit ?? 0;
  const isSubHourlyCheckFrequency = productSlug === "pricetrackr" && limitKey === "min_check_frequency_hours" && rawLimit > 0 && rawLimit < 1;
  const limit = isSubHourlyCheckFrequency ? Math.round(rawLimit * 60) : rawLimit;
  const unit = isSubHourlyCheckFrequency ? " min" : quota.unit ?? meta.unit ?? "";

  return {
    label: quota.label,
    used: quota.used,
    limit,
    unit,
    caption: quota.caption ?? meta.caption,
    mode: quota.mode ?? meta.mode ?? "usage",
  };
}

export function DashboardPlanPanel({
  product,
  plan = "free",
  quotas,
  lockedFeatures,
}: DashboardPlanPanelProps) {
  const [backendPlan, setBackendPlan] = useState<PlanSlug>(plan);
  const [dashboardLimitsByProduct, setDashboardLimitsByProduct] = useState<DashboardLimitProfile>({});
  const activePlan = backendPlan;
  const activeQuotas = useMemo(() => {
    const baseQuotas = quotas && quotas.length ? quotas : defaultQuotaByProduct[product.slug];
    return baseQuotas.map((quota) => resolveQuotaLimit(product.slug, activePlan, quota, dashboardLimitsByProduct));
  }, [activePlan, dashboardLimitsByProduct, product.slug, quotas]);
  const activeLocked = lockedFeatures && lockedFeatures.length ? lockedFeatures : defaultLockedByProduct[product.slug];
  const proPlan = product.plans.find((item) => item.slug === "pro");
  const teamPlan = product.plans.find((item) => item.slug === "team");

  useEffect(() => {
    let mounted = true;

    apiClient
      .get<ProfilePlanResponse>("/auth/profile")
      .then(({ data }) => {
        if (!mounted) return;
        const nextPlan = normalizePlan(data.plans_by_product?.[product.slug]);
        if (nextPlan) setBackendPlan(nextPlan);
        if (data.dashboard_limits_by_product) setDashboardLimitsByProduct(data.dashboard_limits_by_product);
      })
      .catch(() => {
        if (mounted) setBackendPlan(plan);
      });

    return () => {
      mounted = false;
    };
  }, [plan, product.slug]);

  return (
    <div className="dashboard-motion space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>
            Plan and usage
          </p>
          <h2 className="mt-1 text-xl font-semibold" style={{ color: "var(--color-text)" }}>
            {product.name} {activePlan.toUpperCase()} workspace
          </h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusBadge tone={activePlan === "free" ? "neutral" : activePlan === "pro" ? "accent" : "success"}>{activePlan}</StatusBadge>
          <StatusBadge tone="accent">{activePlan === "pro" ? "Current Pro" : `${proPlan?.priceLabel || "$9.99"} Pro`}</StatusBadge>
          <StatusBadge tone="success">{activePlan === "team" ? "Current Team" : `${teamPlan?.priceLabel || "$49"} Team`}</StatusBadge>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {activeQuotas.map((quota) => (
          <UsageQuotaCard key={quota.label} {...quota} tone={quota.used >= quota.limit ? "warning" : "accent"} />
        ))}
      </div>

      {activePlan === "free" ? (
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
            <IntegrationCard key={feature} name={feature} description="Active on your current plan." status="Unlocked" tone="success" />
          ))}
        </div>
      )}
    </div>
  );
}
