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

const planQuotaByProduct: Record<PlanSlug, Partial<Record<DevForgeProduct["slug"], Record<string, Pick<DashboardQuota, "limit" | "unit" | "caption">>>>> = {
  free: {
    filecleaner: {
      "File size": { limit: 10, unit: " MB", caption: "Free max upload before Pro." },
      Retention: { limit: 1, unit: " day", caption: "Free file retention." },
      "Files in history": { limit: 10, caption: "Free workspace visibility before Pro/Team retention." },
    },
    webhookmonitor: {
      "Events today": { limit: 100, caption: "Free daily delivery quota." },
      Endpoints: { limit: 1, caption: "Free endpoint quota." },
    },
    feedbacklens: {
      "Feedback this month": { limit: 100, caption: "Free monthly analysis quota." },
      Sources: { limit: 2, caption: "Free manual and email source quota." },
    },
    pricetrackr: {
      "Active trackers": { limit: 5, caption: "Free active tracker quota." },
      "Watched links": { limit: 5, caption: "Free watched link quota." },
      "Check frequency": { limit: 24, unit: " h", caption: "Free checks run daily." },
    },
    invoicefollow: {
      "Active invoices": { limit: 5, caption: "Free active invoice quota." },
      "Emails this month": { limit: 25, caption: "Free monthly reminder quota." },
      "NLP reply analyses": { limit: 10, caption: "Free reply classification quota." },
    },
  },
  pro: {
    filecleaner: {
      "File size": { limit: 100, unit: " MB", caption: "Pro max upload." },
      Retention: { limit: 2, unit: " days", caption: "Pro file retention." },
      "Files in history": { limit: 100, caption: "Pro workspace visibility." },
    },
    webhookmonitor: {
      "Events today": { limit: 10000, caption: "Pro daily delivery quota." },
      Endpoints: { limit: 10, caption: "Pro endpoint quota." },
    },
    feedbacklens: {
      "Feedback this month": { limit: 5000, caption: "Pro monthly analysis quota." },
      Sources: { limit: 10, caption: "Pro source quota." },
    },
    pricetrackr: {
      "Active trackers": { limit: 100, caption: "Pro active tracker quota." },
      "Watched links": { limit: 100, caption: "Pro watched link quota." },
      "Check frequency": { limit: 1, unit: " h", caption: "Pro checks hourly." },
    },
    invoicefollow: {
      "Active invoices": { limit: 50, caption: "Pro active invoice quota." },
      "Emails this month": { limit: 500, caption: "Pro monthly reminder quota." },
      "NLP reply analyses": { limit: 200, caption: "Pro reply classification quota." },
    },
  },
  team: {
    filecleaner: {
      "File size": { limit: 500, unit: " MB", caption: "Team max upload." },
      Retention: { limit: 7, unit: " days", caption: "Team file retention." },
      "Files in history": { limit: 500, caption: "Team workspace visibility." },
    },
    webhookmonitor: {
      "Events today": { limit: 50000, caption: "Team daily delivery quota." },
      Endpoints: { limit: 50, caption: "Team endpoint quota." },
    },
    feedbacklens: {
      "Feedback this month": { limit: 25000, caption: "Team monthly analysis quota." },
      Sources: { limit: 50, caption: "Team source quota." },
    },
    pricetrackr: {
      "Active trackers": { limit: 500, caption: "Team active tracker quota." },
      "Watched links": { limit: 500, caption: "Team watched link quota." },
      "Check frequency": { limit: 10, unit: " min", caption: "Team checks every 10 minutes." },
    },
    invoicefollow: {
      "Active invoices": { limit: 200, caption: "Team active invoice quota." },
      "Emails this month": { limit: 2000, caption: "Team monthly reminder quota." },
      "NLP reply analyses": { limit: 1000, caption: "Team reply classification quota." },
    },
  },
};

const teamQuotaByProduct = planQuotaByProduct.team;

interface ProfilePlanResponse {
  plans_by_product?: Partial<Record<DevForgeProduct["slug"], PlanSlug>>;
}

function normalizePlan(value: string | undefined): PlanSlug | null {
  return value === "free" || value === "pro" || value === "team" ? value : null;
}

export function DashboardPlanPanel({
  product,
  plan = "free",
  quotas,
  lockedFeatures,
}: DashboardPlanPanelProps) {
  const [backendPlan, setBackendPlan] = useState<PlanSlug>(plan);
  const activePlan = backendPlan;
  const activeQuotas = useMemo(() => {
    const baseQuotas = quotas && quotas.length ? quotas : defaultQuotaByProduct[product.slug];
    const planQuotas = planQuotaByProduct[activePlan]?.[product.slug] || {};

    return baseQuotas.map((quota) => ({
      ...quota,
      ...(planQuotas[quota.label] || {}),
    }));
  }, [activePlan, product.slug, quotas]);
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
          <StatusBadge tone="accent">{proPlan?.priceLabel || "$9.99"} Pro</StatusBadge>
          <StatusBadge tone="success">{teamPlan?.priceLabel || "$49"} Team</StatusBadge>
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
            <IntegrationCard key={feature} name={feature} description="Available based on your current paid plan and backend limits." status="Unlocked" tone="success" />
          ))}
        </div>
      )}
    </div>
  );
}
