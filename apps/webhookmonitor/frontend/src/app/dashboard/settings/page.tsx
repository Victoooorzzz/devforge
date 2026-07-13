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
  fallback_url: string;
  expected_interval_minutes: number;
  alert_email: string;
  slack_webhook_url: string;
  discord_webhook_url: string;
  auto_retry_enabled: boolean;
  retry_max_attempts: number;
  retry_backoff_seconds: number[];
  forward_timeout_seconds: number;
  signature_provider: string;
  signature_secret: string;
  signature_secret_set?: boolean;
  ip_whitelist: string;
  ip_blacklist: string;
  json_schema: string;
  schema_validation_enabled: boolean;
};

type ForwardRule = {
  id: number;
  name: string;
  match_path: string;
  match_equals: string;
  forward_url: string;
  fallback_url: string;
  auto_retry_enabled: boolean;
  is_active: boolean;
};

type ForwardRuleDraft = Omit<ForwardRule, "id" | "is_active">;

const emptyProfile: Profile = {
  name: "",
  email: "",
  has_active_subscription: false,
  is_on_trial: false,
  has_access: false,
  trial_ends_at: null,
};

const emptyForwardRule: ForwardRuleDraft = {
  name: "",
  match_path: "event",
  match_equals: "",
  forward_url: "",
  fallback_url: "",
  auto_retry_enabled: true,
};

export default function SettingsPage() {
  const [profile, setProfile] = useState<Profile>(emptyProfile);
  const [webhookSettings, setWebhookSettings] = useState<WebhookSettings>({
    forward_url: "",
    fallback_url: "",
    expected_interval_minutes: 0,
    alert_email: "",
    slack_webhook_url: "",
    discord_webhook_url: "",
    auto_retry_enabled: false,
    retry_max_attempts: 3,
    retry_backoff_seconds: [1, 2, 4],
    forward_timeout_seconds: 30,
    signature_provider: "",
    signature_secret: "",
    signature_secret_set: false,
    ip_whitelist: "",
    ip_blacklist: "",
    json_schema: "",
    schema_validation_enabled: false,
  });
  const [forwardRules, setForwardRules] = useState<ForwardRule[]>([]);
  const [newForwardRule, setNewForwardRule] = useState<ForwardRuleDraft>(emptyForwardRule);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingWebhook, setSavingWebhook] = useState(false);
  const [savingRule, setSavingRule] = useState(false);
  const [deletingRuleId, setDeletingRuleId] = useState<number | null>(null);
  const [managingSubscription, setManagingSubscription] = useState(false);
  const [confirmClearHistory, setConfirmClearHistory] = useState(false);
  const [clearingHistory, setClearingHistory] = useState(false);
  const [toast, setToast] = useState<DashboardToast | null>(null);

  useEffect(() => {
    let mounted = true;

    async function loadSettings() {
      try {
        const [profileResponse, webhookResponse, rulesResponse] = await Promise.all([
          apiClient.get<Profile>("/auth/profile"),
          apiClient.get<WebhookSettings>("/settings/webhook-prefs"),
          apiClient.get<ForwardRule[]>("/webhooks/forward-rules"),
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
          fallback_url: webhookResponse.data.fallback_url || "",
          expected_interval_minutes: webhookResponse.data.expected_interval_minutes || 0,
          alert_email: webhookResponse.data.alert_email || "",
          slack_webhook_url: webhookResponse.data.slack_webhook_url || "",
          discord_webhook_url: webhookResponse.data.discord_webhook_url || "",
          auto_retry_enabled: Boolean(webhookResponse.data.auto_retry_enabled),
          retry_max_attempts: webhookResponse.data.retry_max_attempts || 3,
          retry_backoff_seconds: webhookResponse.data.retry_backoff_seconds || [1, 2, 4],
          forward_timeout_seconds: webhookResponse.data.forward_timeout_seconds || 30,
          signature_provider: webhookResponse.data.signature_provider || "",
          signature_secret: "",
          signature_secret_set: Boolean(webhookResponse.data.signature_secret_set),
          ip_whitelist: webhookResponse.data.ip_whitelist || "",
          ip_blacklist: webhookResponse.data.ip_blacklist || "",
          json_schema: webhookResponse.data.json_schema || "",
          schema_validation_enabled: Boolean(webhookResponse.data.schema_validation_enabled),
        });
        setForwardRules(rulesResponse.data);
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
        fallback_url: webhookSettings.fallback_url,
        expected_interval_minutes: webhookSettings.expected_interval_minutes,
        alert_email: webhookSettings.alert_email,
        slack_webhook_url: webhookSettings.slack_webhook_url,
        discord_webhook_url: webhookSettings.discord_webhook_url,
        auto_retry_enabled: webhookSettings.auto_retry_enabled,
        retry_max_attempts: webhookSettings.retry_max_attempts,
        retry_backoff_seconds: webhookSettings.retry_backoff_seconds,
        forward_timeout_seconds: webhookSettings.forward_timeout_seconds,
        signature_provider: webhookSettings.signature_provider,
        signature_secret: webhookSettings.signature_secret,
        ip_whitelist: webhookSettings.ip_whitelist,
        ip_blacklist: webhookSettings.ip_blacklist,
        json_schema: webhookSettings.json_schema,
        schema_validation_enabled: webhookSettings.schema_validation_enabled,
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

  const handleForwardRuleSave = async (event: FormEvent) => {
    event.preventDefault();
    if (savingRule) return;

    setSavingRule(true);
    trackEvent("settings_updated", { section: "conditional_forwarding" });

    try {
      const { data } = await apiClient.post<ForwardRule>("/webhooks/forward-rules", {
        name: newForwardRule.name,
        match_path: newForwardRule.match_path,
        match_equals: newForwardRule.match_equals,
        forward_url: newForwardRule.forward_url,
        fallback_url: newForwardRule.fallback_url,
        auto_retry_enabled: newForwardRule.auto_retry_enabled,
        is_active: true,
      });
      setForwardRules([data, ...forwardRules]);
      setNewForwardRule(emptyForwardRule);
      setToast({ tone: "success", message: "Conditional forwarding rule saved." });
    } catch (error) {
      setToast({
        tone: "error",
        message: getSettingsErrorMessage(error, "Failed to save conditional forwarding rule."),
      });
    } finally {
      setSavingRule(false);
    }
  };

  const handleDeleteForwardRule = async (ruleId: number) => {
    if (deletingRuleId) return;

    setDeletingRuleId(ruleId);
    trackEvent("settings_updated", { section: "conditional_forwarding_delete" });

    try {
      await apiClient.delete(`/webhooks/forward-rules/${ruleId}`);
      setForwardRules(forwardRules.filter((rule) => rule.id !== ruleId));
      setToast({ tone: "success", message: "Conditional forwarding rule deleted." });
    } catch (error) {
      setToast({
        tone: "error",
        message: getSettingsErrorMessage(error, "Failed to delete conditional forwarding rule."),
      });
    } finally {
      setDeletingRuleId(null);
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
      await apiClient.delete("/webhooks/requests?confirm=CONFIRM");
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
                  Fallback URL
                </label>
                <input
                  type="url"
                  value={webhookSettings.fallback_url}
                  onChange={(event) => setWebhookSettings({ ...webhookSettings, fallback_url: event.target.value })}
                  className="input-field w-full"
                  placeholder="https://backup.example.com/webhooks"
                  disabled={savingWebhook}
                />
                <p className="mt-1.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                  Used only after configured retry attempts are exhausted.
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                    Retry Attempts
                  </label>
                  <select
                    value={webhookSettings.retry_max_attempts}
                    onChange={(event) =>
                      setWebhookSettings({ ...webhookSettings, retry_max_attempts: Number(event.target.value) })
                    }
                    className="input-field w-full"
                    disabled={savingWebhook}
                  >
                    {[1, 2, 3].map((attempts) => (
                      <option key={attempts} value={attempts}>{attempts}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                    Backoff Seconds
                  </label>
                  <input
                    value={webhookSettings.retry_backoff_seconds.join(",")}
                    onChange={(event) =>
                      setWebhookSettings({
                        ...webhookSettings,
                        retry_backoff_seconds: event.target.value
                          .split(",")
                          .map((value) => Number(value.trim()))
                          .filter((value) => Number.isFinite(value) && value > 0)
                          .slice(0, 3),
                      })
                    }
                    className="input-field w-full"
                    placeholder="1,2,4"
                    disabled={savingWebhook}
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                    Forward Timeout
                  </label>
                  <select
                    value={webhookSettings.forward_timeout_seconds}
                    onChange={(event) =>
                      setWebhookSettings({ ...webhookSettings, forward_timeout_seconds: Number(event.target.value) })
                    }
                    className="input-field w-full"
                    disabled={savingWebhook}
                  >
                    {[10, 30, 60].map((seconds) => (
                      <option key={seconds} value={seconds}>{seconds}s</option>
                    ))}
                  </select>
                </div>
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

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                    Slack Webhook URL
                  </label>
                  <input
                    type="url"
                    value={webhookSettings.slack_webhook_url}
                    onChange={(event) => setWebhookSettings({ ...webhookSettings, slack_webhook_url: event.target.value })}
                    className="input-field w-full"
                    placeholder="https://hooks.slack.com/services/..."
                    disabled={savingWebhook}
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                    Discord Webhook URL
                  </label>
                  <input
                    type="url"
                    value={webhookSettings.discord_webhook_url}
                    onChange={(event) => setWebhookSettings({ ...webhookSettings, discord_webhook_url: event.target.value })}
                    className="input-field w-full"
                    placeholder="https://discord.com/api/webhooks/..."
                    disabled={savingWebhook}
                  />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                    Signature Provider
                  </label>
                  <select
                    value={webhookSettings.signature_provider}
                    onChange={(event) =>
                      setWebhookSettings({ ...webhookSettings, signature_provider: event.target.value })
                    }
                    className="input-field w-full"
                    disabled={savingWebhook}
                  >
                    <option value="">Disabled</option>
                    <option value="stripe">Stripe</option>
                    <option value="github">GitHub</option>
                    <option value="shopify">Shopify</option>
                    <option value="generic">Generic X-Signature</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                    Signature Secret
                  </label>
                  <input
                    type="password"
                    value={webhookSettings.signature_secret}
                    onChange={(event) => setWebhookSettings({ ...webhookSettings, signature_secret: event.target.value })}
                    className="input-field w-full"
                    placeholder={webhookSettings.signature_secret_set ? "Secret already saved" : "whsec_..."}
                    disabled={savingWebhook}
                  />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                    IP Whitelist
                  </label>
                  <input
                    value={webhookSettings.ip_whitelist}
                    onChange={(event) => setWebhookSettings({ ...webhookSettings, ip_whitelist: event.target.value })}
                    className="input-field w-full"
                    placeholder="1.2.3.4, 5.6.7.0/24"
                    disabled={savingWebhook}
                  />
                  <p className="mt-1.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                    Comma-separated IPs/CIDRs. Only allowed IPs can post.
                  </p>
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                    IP Blacklist
                  </label>
                  <input
                    value={webhookSettings.ip_blacklist}
                    onChange={(event) => setWebhookSettings({ ...webhookSettings, ip_blacklist: event.target.value })}
                    className="input-field w-full"
                    placeholder="9.9.9.9"
                    disabled={savingWebhook}
                  />
                  <p className="mt-1.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                    Blocked IPs/CIDRs.
                  </p>
                </div>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                  JSON Schema Validation
                </label>
                <textarea
                  value={webhookSettings.json_schema}
                  onChange={(event) => setWebhookSettings({ ...webhookSettings, json_schema: event.target.value })}
                  className="input-field w-full font-mono text-xs"
                  rows={6}
                  placeholder='{ "type": "object", "properties": { "event": { "type": "string" } } }'
                  disabled={savingWebhook}
                />
                <p className="mt-1.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                  Validate payload structure at ingestion.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium" style={{ color: "var(--color-text)" }}>
                    Enforce Schema Validation
                  </p>
                  <p className="mt-0.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                    Flag ingested requests matching the schema.
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={webhookSettings.schema_validation_enabled}
                  onClick={() =>
                    setWebhookSettings({
                      ...webhookSettings,
                      schema_validation_enabled: !webhookSettings.schema_validation_enabled,
                    })
                  }
                  className="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-60"
                  style={{
                    backgroundColor: webhookSettings.schema_validation_enabled
                      ? "var(--color-accent)"
                      : "var(--color-border)",
                  }}
                  disabled={savingWebhook}
                >
                  <span
                    className="inline-block h-5 w-5 transform rounded-full bg-white shadow transition duration-200"
                    style={{ transform: webhookSettings.schema_validation_enabled ? "translateX(20px)" : "translateX(0)" }}
                  />
                </button>
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

            <div className="mb-6 pt-6" style={{ borderTop: "1px solid var(--color-border)" }}>
              <h3 className="mb-2 text-base font-medium" style={{ color: "var(--color-text)" }}>
                Conditional Forwarding
              </h3>
              <p className="mb-4 text-sm leading-6" style={{ color: "var(--color-text-secondary)" }}>
                Route matched payloads to a primary URL and optionally fail over to a fallback URL. Rules are matched sequentially in order of creation.
              </p>

              <form onSubmit={handleForwardRuleSave} className="max-w-2xl space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                      Rule Name
                    </label>
                    <input
                      value={newForwardRule.name}
                      onChange={(event) => setNewForwardRule({ ...newForwardRule, name: event.target.value })}
                      className="input-field w-full"
                      placeholder="Stripe paid events"
                      disabled={savingRule}
                      required
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                      Match Path
                    </label>
                    <input
                      value={newForwardRule.match_path}
                      onChange={(event) => setNewForwardRule({ ...newForwardRule, match_path: event.target.value })}
                      className="input-field w-full"
                      placeholder="event"
                      disabled={savingRule}
                      required
                    />
                    <p className="mt-1.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                      Use dot paths such as event or data.type.
                    </p>
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                      Match Value
                    </label>
                    <input
                      value={newForwardRule.match_equals}
                      onChange={(event) => setNewForwardRule({ ...newForwardRule, match_equals: event.target.value })}
                      className="input-field w-full"
                      placeholder="invoice.paid"
                      disabled={savingRule}
                      required
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                      Primary Forward URL
                    </label>
                    <input
                      type="url"
                      value={newForwardRule.forward_url}
                      onChange={(event) => setNewForwardRule({ ...newForwardRule, forward_url: event.target.value })}
                      className="input-field w-full"
                      placeholder="https://api.example.com/webhooks/paid"
                      disabled={savingRule}
                      required
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                      Fallback URL
                    </label>
                    <input
                      type="url"
                      value={newForwardRule.fallback_url}
                      onChange={(event) => setNewForwardRule({ ...newForwardRule, fallback_url: event.target.value })}
                      className="input-field w-full"
                      placeholder="https://backup.example.com/webhooks"
                      disabled={savingRule}
                    />
                  </div>
                  <div className="flex flex-col justify-end gap-3">
                    <button
                      type="button"
                      role="switch"
                      aria-checked={newForwardRule.auto_retry_enabled}
                      onClick={() =>
                        setNewForwardRule({
                          ...newForwardRule,
                          auto_retry_enabled: !newForwardRule.auto_retry_enabled,
                        })
                      }
                      className="flex items-center justify-between rounded-lg px-4 py-3 text-left text-sm transition-colors"
                      style={{
                        backgroundColor: "var(--color-surface)",
                        border: "1px solid var(--color-border)",
                        color: "var(--color-text)",
                      }}
                      disabled={savingRule}
                    >
                      <span>Retry matched forwards</span>
                      <span
                        className="relative inline-flex h-6 w-11 flex-shrink-0 rounded-full border-2 border-transparent transition-colors"
                        style={{
                          backgroundColor: newForwardRule.auto_retry_enabled
                            ? "var(--color-accent)"
                            : "var(--color-border)",
                        }}
                      >
                        <span
                          className="inline-block h-5 w-5 transform rounded-full bg-white shadow transition duration-200"
                          style={{ transform: newForwardRule.auto_retry_enabled ? "translateX(20px)" : "translateX(0)" }}
                        />
                      </span>
                    </button>
                  </div>
                </div>

                <button type="submit" className="btn-primary" disabled={savingRule}>
                  {savingRule ? "Saving Rule..." : "Save Conditional Rule"}
                </button>
              </form>

              {forwardRules.length > 0 ? (
                <div className="mt-6 space-y-3">
                  {forwardRules.map((rule) => (
                    <div
                      key={rule.id}
                      className="rounded-lg p-4"
                      style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}
                    >
                      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>
                            {rule.name}
                          </p>
                          <p className="mt-1 font-mono text-xs" style={{ color: "var(--color-text-secondary)" }}>
                            {rule.match_path} = {rule.match_equals}
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleDeleteForwardRule(rule.id)}
                          className="rounded-md border border-red-500/20 bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-500 transition-colors hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                          disabled={deletingRuleId === rule.id}
                        >
                          {deletingRuleId === rule.id ? "Deleting..." : "Delete Rule"}
                        </button>
                      </div>
                      <div className="space-y-1 font-mono text-xs" style={{ color: "var(--color-text-secondary)" }}>
                        <p className="break-all">Primary: {rule.forward_url}</p>
                        {rule.fallback_url ? <p className="break-all">Fallback: {rule.fallback_url}</p> : null}
                        <p>Retry: {rule.auto_retry_enabled ? "enabled" : "disabled"}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>

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
