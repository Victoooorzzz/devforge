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

type WebhookSettings = {
  forward_url: string;
  expected_interval_minutes: number;
  alert_email: string;
  auto_retry_enabled: boolean;
};

const emptyProfile: Profile = {
  name: "",
  email: "",
  has_active_subscription: false,
  is_on_trial: false,
  has_access: false,
  trial_ends_at: null,
};

export default function SettingsPage() {
  const [profile, setProfile] = useState<Profile>(emptyProfile);
  const [webhookSettings, setWebhookSettings] = useState<WebhookSettings>({
    forward_url: "",
    expected_interval_minutes: 0,
    alert_email: "",
    auto_retry_enabled: false,
  });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingWebhook, setSavingWebhook] = useState(false);
  const [managingSubscription, setManagingSubscription] = useState(false);
  const [confirmClearHistory, setConfirmClearHistory] = useState(false);
  const [clearingHistory, setClearingHistory] = useState(false);
  const [toast, setToast] = useState<DashboardToast | null>(null);

  useEffect(() => {
    let mounted = true;

    async function loadSettings() {
      try {
        const [profileResponse, webhookResponse] = await Promise.all([
          apiClient.get<Profile>("/auth/profile"),
          apiClient.get<WebhookSettings>("/settings/webhook-prefs"),
        ]);

        if (!mounted) return;

        const profileData = profileResponse.data;
        setProfile({
          name: profileData.name || "",
          email: profileData.email || "",
          has_active_subscription: Boolean(profileData.has_active_subscription),
          is_on_trial: Boolean(profileData.is_on_trial),
          has_access: Boolean(profileData.has_access),
          trial_ends_at: profileData.trial_ends_at || null,
        });
        setWebhookSettings({
          forward_url: webhookResponse.data.forward_url || "",
          expected_interval_minutes: webhookResponse.data.expected_interval_minutes || 0,
          alert_email: webhookResponse.data.alert_email || "",
          auto_retry_enabled: Boolean(webhookResponse.data.auto_retry_enabled),
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

  const handleWebhookSave = async (event: FormEvent) => {
    event.preventDefault();
    if (savingWebhook) return;

    setSavingWebhook(true);
    trackEvent("settings_updated", { section: "webhook_prefs" });

    try {
      await apiClient.put("/settings/webhook-prefs", {
        forward_url: webhookSettings.forward_url,
        expected_interval_minutes: webhookSettings.expected_interval_minutes,
        alert_email: webhookSettings.alert_email,
        auto_retry_enabled: webhookSettings.auto_retry_enabled,
      });
      setToast({ tone: "success", message: "Webhook preferences updated successfully." });
    } catch (error) {
      setToast({
        tone: "error",
        message: getSettingsErrorMessage(error, "Failed to update webhook preferences."),
      });
    } finally {
      setSavingWebhook(false);
    }
  };

  const handleClearHistory = async () => {
    if (clearingHistory) return;

    if (!confirmClearHistory) {
      setConfirmClearHistory(true);
      setToast({
        tone: "info",
        message: "Click Confirm Clear History to permanently delete captured webhook requests.",
      });
      return;
    }

    setClearingHistory(true);
    trackEvent("webhook_history_cleared");

    try {
      await apiClient.delete("/webhooks/requests");
      setConfirmClearHistory(false);
      setToast({ tone: "success", message: "Webhook request history cleared successfully." });
    } catch (error) {
      setToast({
        tone: "error",
        message: getSettingsErrorMessage(error, "Failed to clear webhook request history."),
      });
    } finally {
      setClearingHistory(false);
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
            title="Webhook Preferences"
            description="Forward captured webhook requests to your own endpoint for downstream processing."
          >
            <form onSubmit={handleWebhookSave} className="mb-6 max-w-md space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                  Forward URL
                </label>
                <input
                  type="url"
                  value={webhookSettings.forward_url}
                  onChange={(event) => setWebhookSettings({ ...webhookSettings, forward_url: event.target.value })}
                  className="input-field w-full"
                  placeholder="https://your-server.com/api/webhooks"
                  disabled={savingWebhook}
                />
                <p className="mt-1.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                  Leave this blank to capture requests without forwarding them.
                </p>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                  Silence Alert Interval
                </label>
                <input
                  type="number"
                  min="0"
                  step="5"
                  value={webhookSettings.expected_interval_minutes}
                  onChange={(event) =>
                    setWebhookSettings({
                      ...webhookSettings,
                      expected_interval_minutes: Math.max(0, Number(event.target.value) || 0),
                    })
                  }
                  className="input-field w-full"
                  disabled={savingWebhook}
                />
                <p className="mt-1.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                  Use 0 to disable silence checks; otherwise alerts trigger after roughly 2 missed intervals.
                </p>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                  Alert Email
                </label>
                <input
                  type="email"
                  value={webhookSettings.alert_email}
                  onChange={(event) => setWebhookSettings({ ...webhookSettings, alert_email: event.target.value })}
                  className="input-field w-full"
                  placeholder="alerts@example.com"
                  disabled={savingWebhook}
                />
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium" style={{ color: "var(--color-text)" }}>
                    Auto Retry Forwarding
                  </p>
                  <p className="mt-0.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                    Queue failed forwards for exponential backoff retries.
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={webhookSettings.auto_retry_enabled}
                  onClick={() =>
                    setWebhookSettings({
                      ...webhookSettings,
                      auto_retry_enabled: !webhookSettings.auto_retry_enabled,
                    })
                  }
                  className="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-60"
                  style={{
                    backgroundColor: webhookSettings.auto_retry_enabled
                      ? "var(--color-accent)"
                      : "var(--color-border)",
                  }}
                  disabled={savingWebhook}
                >
                  <span
                    className="inline-block h-5 w-5 transform rounded-full bg-white shadow transition duration-200"
                    style={{ transform: webhookSettings.auto_retry_enabled ? "translateX(20px)" : "translateX(0)" }}
                  />
                </button>
              </div>
              <button type="submit" className="btn-primary" disabled={savingWebhook}>
                {savingWebhook ? "Saving..." : "Save Preferences"}
              </button>
            </form>

            <div className="pt-6" style={{ borderTop: "1px solid var(--color-border)" }}>
              <h3 className="mb-2 text-base font-medium text-red-500">Danger Zone</h3>
              <p className="mb-4 text-sm leading-6" style={{ color: "var(--color-text-secondary)" }}>
                Permanently delete all captured webhook requests. This cannot be undone.
              </p>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={handleClearHistory}
                  disabled={clearingHistory}
                  className="rounded-md border border-red-500/20 bg-red-500/10 px-4 py-2 text-sm font-medium text-red-500 transition-colors hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {clearingHistory
                    ? "Clearing..."
                    : confirmClearHistory
                      ? "Confirm Clear History"
                      : "Clear History"}
                </button>
                {confirmClearHistory ? (
                  <button
                    type="button"
                    onClick={() => setConfirmClearHistory(false)}
                    className="btn-secondary"
                    disabled={clearingHistory}
                  >
                    Cancel
                  </button>
                ) : null}
              </div>
            </div>
          </SettingsSection>
        </>
      )}
    </div>
  );
}
