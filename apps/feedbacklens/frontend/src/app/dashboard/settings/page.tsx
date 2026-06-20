"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiClient, trackEvent } from "@devforge/core";
import {
  ActionToast,
  getSettingsErrorMessage,
  SettingsLoading,
  SettingsSection,
  SubscriptionPanel,
  type DashboardToast,
  type SettingsSubscriptionProfile,
} from "@devforge/ui";
import { product } from "@/config/product";

type Profile = SettingsSubscriptionProfile & {
  name: string;
  email: string;
  has_access: boolean;
};

type FeedbackSettings = {
  custom_prompt: string;
  negative_threshold: number;
  alert_email: string;
  weekly_summary_enabled: boolean;
};

const emptyProfile: Profile = {
  name: "",
  email: "",
  has_active_subscription: false,
  is_on_trial: false,
  has_access: false,
  trial_ends_at: null,
};

function normalizeNegativeThreshold(value: number | null | undefined) {
  if (typeof value !== "number" || Number.isNaN(value)) return 0.5;
  if (value > 1) return 0.5;
  return Math.min(1, Math.max(0, value));
}

export default function SettingsPage() {
  const [profile, setProfile] = useState<Profile>(emptyProfile);
  const [feedbackSettings, setFeedbackSettings] = useState<FeedbackSettings>({
    custom_prompt: "",
    negative_threshold: 0.5,
    alert_email: "",
    weekly_summary_enabled: true,
  });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingFeedback, setSavingFeedback] = useState(false);
  const [managingSubscription, setManagingSubscription] = useState(false);
  const [toast, setToast] = useState<DashboardToast | null>(null);

  useEffect(() => {
    let mounted = true;

    async function loadSettings() {
      try {
        const [profileResponse, feedbackResponse] = await Promise.all([
          apiClient.get<Profile>("/auth/profile"),
          apiClient.get<FeedbackSettings>("/settings/feedback-prefs"),
        ]);

        if (!mounted) return;

        const profileData = profileResponse.data;
        const feedbackData = feedbackResponse.data;
        setProfile({
          name: profileData.name || "",
          email: profileData.email || "",
          has_active_subscription: Boolean(profileData.has_active_subscription),
          is_on_trial: Boolean(profileData.is_on_trial),
          has_access: Boolean(profileData.has_access),
          trial_ends_at: profileData.trial_ends_at || null,
        });
        setFeedbackSettings({
          custom_prompt: feedbackData.custom_prompt || "",
          negative_threshold: normalizeNegativeThreshold(feedbackData.negative_threshold),
          alert_email: feedbackData.alert_email || "",
          weekly_summary_enabled: feedbackData.weekly_summary_enabled ?? true,
        });
      } catch (error) {
        const message = getSettingsErrorMessage(error, "We could not load your settings.");
        if (!mounted) return;
        setLoadError(message);
        setToast({ tone: "error", message });
      } finally {
        if (mounted) setLoading(false);
      }
    }

    loadSettings();
    return () => {
      mounted = false;
    };
  }, []);

  const handleProfileSave = async (event: FormEvent) => {
    event.preventDefault();
    if (savingProfile) return;

    setSavingProfile(true);
    trackEvent("settings_updated", { section: "profile" });

    try {
      await apiClient.put("/auth/profile", { name: profile.name, email: profile.email });
      setToast({ tone: "success", message: "Profile updated successfully." });
    } catch (error) {
      setToast({
        tone: "error",
        message: getSettingsErrorMessage(error, "Failed to update profile."),
      });
    } finally {
      setSavingProfile(false);
    }
  };

  const handleFeedbackSave = async (event: FormEvent) => {
    event.preventDefault();
    if (savingFeedback) return;

    setSavingFeedback(true);
    trackEvent("settings_updated", { section: "feedback_prefs" });

    try {
      await apiClient.put("/settings/feedback-prefs", {
        custom_prompt: feedbackSettings.custom_prompt,
        negative_threshold: Number(feedbackSettings.negative_threshold),
        alert_email: feedbackSettings.alert_email,
        weekly_summary_enabled: feedbackSettings.weekly_summary_enabled,
      });
      setToast({ tone: "success", message: "Feedback preferences updated successfully." });
    } catch (error) {
      setToast({
        tone: "error",
        message: getSettingsErrorMessage(error, "Failed to update feedback preferences."),
      });
    } finally {
      setSavingFeedback(false);
    }
  };

  const openBillingUrl = (url: string, successMessage: string) => {
    const opened = window.open(url, "_blank", "noopener,noreferrer");
    if (!opened) {
      throw new Error("Your browser blocked the billing window. Allow pop-ups and try again.");
    }
    setToast({ tone: "success", message: successMessage });
  };

  const handleManageSubscription = async () => {
    if (managingSubscription) return;

    setManagingSubscription(true);
    trackEvent("subscription_manage_clicked");

    try {
      if (profile.has_active_subscription) {
        const { data } = await apiClient.get<{ portal_url: string }>("/polar/portal");
        openBillingUrl(data.portal_url, "Billing portal opened in a new tab.");
      } else {
        const { data } = await apiClient.post<{ checkout_url: string }>("/polar/checkout", {
          app_name: product.name,
        });
        openBillingUrl(data.checkout_url, "Checkout opened in a new tab.");
      }
    } catch (error) {
      setToast({
        tone: "error",
        message: getSettingsErrorMessage(error, "Failed to open billing."),
      });
    } finally {
      setManagingSubscription(false);
    }
  };

  const trialDaysLeft = profile.trial_ends_at
    ? Math.max(0, Math.ceil((new Date(profile.trial_ends_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24)))
    : 0;

  if (loading) return <SettingsLoading />;

  return (
    <div className="mx-auto max-w-4xl">
      <ActionToast toast={toast} onDismiss={() => setToast(null)} />
      <h1 className="mb-8 text-2xl font-bold tracking-tight" style={{ color: "var(--color-text)" }}>
        Settings
      </h1>

      {loadError ? (
        <div
          className="rounded-lg p-5"
          style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)" }}
          role="alert"
        >
          <h2 className="mb-2 text-base font-semibold text-red-500">Settings unavailable</h2>
          <p className="mb-4 text-sm leading-6" style={{ color: "var(--color-text-secondary)" }}>
            {loadError}
          </p>
          <button type="button" onClick={() => window.location.reload()} className="btn-secondary">
            Retry
          </button>
        </div>
      ) : (
        <>
          <SettingsSection title="Profile">
            <form onSubmit={handleProfileSave} className="max-w-md space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                  Name
                </label>
                <input
                  value={profile.name}
                  onChange={(event) => setProfile({ ...profile, name: event.target.value })}
                  className="input-field w-full"
                  placeholder="Your name"
                  disabled={savingProfile}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                  Email
                </label>
                <input
                  type="email"
                  value={profile.email}
                  onChange={(event) => setProfile({ ...profile, email: event.target.value })}
                  className="input-field w-full"
                  required
                  disabled={savingProfile}
                />
              </div>
              <button type="submit" className="btn-primary" disabled={savingProfile}>
                {savingProfile ? "Saving..." : "Save Profile"}
              </button>
            </form>
          </SettingsSection>

          <SettingsSection title="Subscription">
            <SubscriptionPanel
              profile={profile}
              trialDaysLeft={trialDaysLeft}
              onManage={handleManageSubscription}
              busy={managingSubscription}
            />
          </SettingsSection>

          <SettingsSection
            title="AI Analysis Preferences"
            description="Tune how feedback is classified and where weekly summaries are sent."
          >
            <form onSubmit={handleFeedbackSave} className="max-w-2xl space-y-6">
              <div>
                <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                  Custom Prompt
                </label>
                <textarea
                  value={feedbackSettings.custom_prompt}
                  onChange={(event) => setFeedbackSettings({ ...feedbackSettings, custom_prompt: event.target.value })}
                  className="input-field h-32 w-full py-3"
                  placeholder="Focus specifically on pricing complaints and feature requests..."
                  disabled={savingFeedback}
                />
                <p className="mt-1.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                  Additional instructions for Gemini when analyzing feedback.
                </p>
              </div>

              <div>
                <div className="mb-1.5 flex justify-between gap-3">
                  <label className="block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                    Negative Threshold
                  </label>
                  <span className="text-sm font-medium" style={{ color: "var(--color-text)" }}>
                    {feedbackSettings.negative_threshold.toFixed(1)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={feedbackSettings.negative_threshold}
                  onChange={(event) =>
                    setFeedbackSettings({ ...feedbackSettings, negative_threshold: parseFloat(event.target.value) })
                  }
                  className="w-full accent-[var(--color-primary)]"
                  disabled={savingFeedback}
                />
                <p className="mt-1.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                  Sentiment below this value will be flagged as negative.
                </p>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                  Alert Email
                </label>
                <input
                  type="email"
                  value={feedbackSettings.alert_email}
                  onChange={(event) => setFeedbackSettings({ ...feedbackSettings, alert_email: event.target.value })}
                  className="input-field w-full"
                  placeholder="you@example.com"
                  disabled={savingFeedback}
                />
                <p className="mt-1.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                  Weekly digest emails will be sent to this address.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium" style={{ color: "var(--color-text)" }}>
                    Weekly Summary Email
                  </p>
                  <p className="mt-0.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                    Receive a weekly digest of your feedback activity.
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={feedbackSettings.weekly_summary_enabled}
                  onClick={() =>
                    setFeedbackSettings({
                      ...feedbackSettings,
                      weekly_summary_enabled: !feedbackSettings.weekly_summary_enabled,
                    })
                  }
                  className="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-60"
                  style={{
                    backgroundColor: feedbackSettings.weekly_summary_enabled
                      ? "var(--color-accent)"
                      : "var(--color-border)",
                  }}
                  disabled={savingFeedback}
                >
                  <span
                    className="inline-block h-5 w-5 transform rounded-full bg-white shadow transition duration-200"
                    style={{ transform: feedbackSettings.weekly_summary_enabled ? "translateX(20px)" : "translateX(0)" }}
                  />
                </button>
              </div>

              <button type="submit" className="btn-primary" disabled={savingFeedback}>
                {savingFeedback ? "Saving..." : "Save AI Preferences"}
              </button>
            </form>
          </SettingsSection>
        </>
      )}
    </div>
  );
}
