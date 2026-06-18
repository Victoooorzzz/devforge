"use client";

import React from "react";
import { InlineSpinner } from "./DashboardUX";

export interface SettingsSubscriptionProfile {
  has_active_subscription: boolean;
  is_on_trial: boolean;
  trial_ends_at: string | null;
}

interface SettingsSectionProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}

export function SettingsSection({ title, description, children, className = "" }: SettingsSectionProps) {
  return (
    <section
      className={`mb-6 rounded-lg p-4 sm:p-6 ${className}`}
      style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}
    >
      <div className="mb-5">
        <h2 className="text-lg font-semibold" style={{ color: "var(--color-text)" }}>
          {title}
        </h2>
        {description ? (
          <p className="mt-1 text-sm leading-6" style={{ color: "var(--color-text-secondary)" }}>
            {description}
          </p>
        ) : null}
      </div>
      {children}
    </section>
  );
}

export function SettingsLoading({ label = "Loading settings..." }: { label?: string }) {
  return (
    <div className="mx-auto max-w-4xl p-4 sm:p-8" style={{ color: "var(--color-text-secondary)" }}>
      <div
        className="inline-flex items-center gap-2 rounded-lg px-4 py-3 text-sm"
        style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}
        role="status"
      >
        <InlineSpinner />
        {label}
      </div>
    </div>
  );
}

interface SubscriptionPanelProps {
  profile: SettingsSubscriptionProfile;
  trialDaysLeft: number;
  onManage: () => void;
  busy?: boolean;
}

export function SubscriptionPanel({ profile, trialDaysLeft, onManage, busy = false }: SubscriptionPanelProps) {
  const isPaid = profile.has_active_subscription;
  const isTrial = profile.is_on_trial && !isPaid;
  const isExpired = !profile.is_on_trial && !isPaid && Boolean(profile.trial_ends_at);
  const trialEndDate = profile.trial_ends_at ? new Date(profile.trial_ends_at).toLocaleDateString() : "soon";

  const statusLabel = isPaid ? "Active Plan" : isTrial ? "Free Trial" : "No active subscription";
  const buttonLabel = isPaid ? "Manage Plan" : isTrial ? "Subscribe Now" : "Subscribe";
  const description = isPaid
    ? "You are currently on a premium plan."
    : isTrial
      ? `Your trial ends on ${trialEndDate}.`
      : "Subscribe to access all features.";

  return (
    <div className="space-y-4">
      {isTrial ? (
        <div
          className="rounded-lg border p-4"
          style={{ backgroundColor: "var(--color-accent-dim)", borderColor: "var(--color-accent)" }}
          role="status"
        >
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <span
              className="rounded-full px-2 py-0.5 text-xs font-semibold uppercase"
              style={{ backgroundColor: "var(--color-accent)", color: "var(--color-background)" }}
            >
              Trial
            </span>
            <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>
              Free Trial Active
            </p>
          </div>
          <p className="text-sm leading-6" style={{ color: "var(--color-text-secondary)" }}>
            You have{" "}
            <strong style={{ color: "var(--color-accent)" }}>
              {trialDaysLeft} day{trialDaysLeft !== 1 ? "s" : ""}
            </strong>{" "}
            remaining. Subscribe now to keep access when your trial ends.
          </p>
        </div>
      ) : null}

      {isExpired ? (
        <div
          className="rounded-lg border p-4"
          style={{ backgroundColor: "rgba(239, 68, 68, 0.1)", borderColor: "rgba(239, 68, 68, 0.3)" }}
          role="alert"
        >
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-red-500 px-2 py-0.5 text-xs font-semibold uppercase text-white">
              Expired
            </span>
            <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>
              Trial Expired
            </p>
          </div>
          <p className="text-sm leading-6" style={{ color: "var(--color-text-secondary)" }}>
            Your free trial has ended. Subscribe to regain access to all features.
          </p>
        </div>
      ) : null}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium" style={{ color: "var(--color-text)" }}>
            {statusLabel}
          </p>
          <p className="mt-1 text-sm leading-6" style={{ color: "var(--color-text-secondary)" }}>
            {description}
          </p>
        </div>
        <button type="button" onClick={onManage} disabled={busy} className="btn-primary shrink-0">
          {busy ? (
            <span className="inline-flex items-center gap-2">
              <InlineSpinner />
              Opening...
            </span>
          ) : (
            buttonLabel
          )}
        </button>
      </div>
    </div>
  );
}

export function getSettingsErrorMessage(error: unknown, fallback: string) {
  const maybe = error as {
    detail?: string;
    response?: { data?: { detail?: string } | string };
    message?: string;
  };
  const responseData = maybe.response?.data;

  if (typeof responseData === "string" && responseData) {
    return responseData;
  }

  if (responseData && typeof responseData === "object" && responseData.detail) {
    return responseData.detail;
  }

  return maybe.detail || maybe.message || fallback;
}
