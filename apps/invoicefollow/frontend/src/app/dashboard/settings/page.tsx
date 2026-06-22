"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
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
import { CheckCircle2, CreditCard, Mail, RefreshCw, Save } from "lucide-react";

type Profile = SettingsSubscriptionProfile & {
  name: string;
  email: string;
  has_access: boolean;
};

interface InvoiceSettings {
  company_name: string;
  send_hour: number;
  skip_weekends: boolean;
  timezone: string;
  sender_name: string;
  weekly_digest_enabled: boolean;
  immediate_alerts_enabled: boolean;
  no_send_after_hour: number;
  forward_address: string;
  connections: {
    gmail: boolean;
    outlook: boolean;
    stripe: boolean;
    paypal: boolean;
  };
}

interface TemplateItem {
  id: string;
  day: number;
  name: string;
  tone: string;
  subject: string;
  body: string;
  enabled: boolean;
}

const emptyProfile: Profile = {
  name: "",
  email: "",
  has_active_subscription: false,
  is_on_trial: false,
  has_access: false,
  trial_ends_at: null,
};

const defaultSettings: InvoiceSettings = {
  company_name: "",
  send_hour: 9,
  skip_weekends: true,
  timezone: "America/Lima",
  sender_name: "",
  weekly_digest_enabled: true,
  immediate_alerts_enabled: true,
  no_send_after_hour: 18,
  forward_address: "",
  connections: { gmail: false, outlook: false, stripe: false, paypal: false },
};

function renderPreview(template: TemplateItem, settings: InvoiceSettings) {
  const values: Record<string, string> = {
    client_name: "Acme Corp",
    invoice_number: "#1042",
    amount: "$4,800.00",
    currency: "USD",
    due_date: "2026-07-15",
    days_overdue: String(template.day),
    company_name: settings.company_name || "Your Company",
    user_name: settings.sender_name || "You",
  };
  return Object.entries(values).reduce((text, [key, value]) => text.replaceAll(`{${key}}`, value), template.body);
}

export default function SettingsPage() {
  const [profile, setProfile] = useState<Profile>(emptyProfile);
  const [invoiceSettings, setInvoiceSettings] = useState<InvoiceSettings>(defaultSettings);
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [savingTemplateId, setSavingTemplateId] = useState<string | null>(null);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [paymentCredentials, setPaymentCredentials] = useState({
    stripe_api_key: "",
    paypal_client_id: "",
    paypal_client_secret: "",
  });
  const [managingSubscription, setManagingSubscription] = useState(false);
  const [toast, setToast] = useState<DashboardToast | null>(null);

  useEffect(() => {
    let mounted = true;
    async function loadSettings() {
      try {
        const [profileResponse, settingsResponse, templateResponse] = await Promise.all([
          apiClient.get<Profile>("/auth/profile"),
          apiClient.get<InvoiceSettings>("/settings"),
          apiClient.get<{ templates: TemplateItem[] }>("/templates"),
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
        setInvoiceSettings({ ...defaultSettings, ...settingsResponse.data });
        setTemplates(templateResponse.data.templates || []);
      } catch (error) {
        const message = getSettingsErrorMessage(error, "We could not load InvoiceFollow settings.");
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

  const trialDaysLeft = profile.trial_ends_at
    ? Math.max(0, Math.ceil((new Date(profile.trial_ends_at).getTime() - Date.now()) / 86400000))
    : 0;

  const connectionRows = useMemo(() => [
    { id: "gmail", label: "Gmail", detail: "OAuth read + send", icon: Mail },
    { id: "outlook", label: "Outlook", detail: "Microsoft Graph read + send", icon: Mail },
    { id: "stripe", label: "Stripe", detail: "Read-only payment matching", icon: CreditCard },
    { id: "paypal", label: "PayPal", detail: "Read-only transaction matching", icon: CreditCard },
  ], []);

  if (loading) return <SettingsLoading />;

  const handleProfileSave = async (event: FormEvent) => {
    event.preventDefault();
    setSavingProfile(true);
    trackEvent("settings_updated", { section: "profile" });
    try {
      await apiClient.put("/auth/profile", { name: profile.name, email: profile.email });
      setToast({ tone: "success", message: "Profile updated." });
    } catch (error) {
      setToast({ tone: "error", message: getSettingsErrorMessage(error, "Failed to update profile.") });
    } finally {
      setSavingProfile(false);
    }
  };

  const handleSettingsSave = async (event: FormEvent) => {
    event.preventDefault();
    setSavingSettings(true);
    trackEvent("settings_updated", { section: "invoicefollow_schedule" });
    try {
      const { data } = await apiClient.put<InvoiceSettings>("/settings", invoiceSettings);
      setInvoiceSettings(data);
      setToast({ tone: "success", message: "InvoiceFollow settings saved." });
    } catch (error) {
      setToast({ tone: "error", message: getSettingsErrorMessage(error, "Failed to update InvoiceFollow settings.") });
    } finally {
      setSavingSettings(false);
    }
  };

  const handleTemplateSave = async (template: TemplateItem) => {
    setSavingTemplateId(template.id);
    trackEvent("settings_updated", { section: "invoicefollow_template", template_id: template.id });
    try {
      await apiClient.put(`/templates/${template.id}`, {
        subject: template.subject,
        body: template.body,
        enabled: template.enabled,
      });
      setToast({ tone: "success", message: `${template.name} template saved.` });
    } catch (error) {
      setToast({ tone: "error", message: getSettingsErrorMessage(error, "Template save failed.") });
    } finally {
      setSavingTemplateId(null);
    }
  };

  const handleConnect = async (provider: string) => {
    setConnecting(provider);
    trackEvent("feature_used", { feature_name: `invoicefollow_connect_${provider}` });
    try {
      const payload =
        provider === "stripe"
          ? { account_label: "Stripe read-only", api_key: paymentCredentials.stripe_api_key }
          : provider === "paypal"
            ? {
                account_label: "PayPal read-only",
                client_id: paymentCredentials.paypal_client_id,
                client_secret: paymentCredentials.paypal_client_secret,
              }
            : { email: profile.email };
      const { data } = await apiClient.post<{ oauth_url?: string; connected?: boolean }>(`/connect/${provider}`, payload);
      if (data.oauth_url && !data.connected) window.open(data.oauth_url, "_blank", "noopener,noreferrer");
      setInvoiceSettings((current) => ({
        ...current,
        connections: { ...current.connections, [provider]: Boolean(data.connected) || provider === "stripe" || provider === "paypal" },
      }));
      setToast({ tone: "success", message: `${provider} connection started.` });
    } catch (error) {
      setToast({ tone: "error", message: getSettingsErrorMessage(error, `Could not connect ${provider}.`) });
    } finally {
      setConnecting(null);
    }
  };

  const openBillingUrl = (url: string, successMessage: string) => {
    const opened = window.open(url, "_blank", "noopener,noreferrer");
    if (!opened) throw new Error("Your browser blocked the billing window. Allow pop-ups and try again.");
    setToast({ tone: "success", message: successMessage });
  };

  const handleManageSubscription = async () => {
    setManagingSubscription(true);
    trackEvent("subscription_manage_clicked");
    try {
      if (profile.has_active_subscription) {
        const { data } = await apiClient.get<{ portal_url: string }>("/polar/portal");
        openBillingUrl(data.portal_url, "Billing portal opened.");
      } else {
        const { data } = await apiClient.post<{ checkout_url: string }>("/polar/checkout", { app_name: product.name });
        openBillingUrl(data.checkout_url, "Checkout opened.");
      }
    } catch (error) {
      setToast({ tone: "error", message: getSettingsErrorMessage(error, "Failed to open billing.") });
    } finally {
      setManagingSubscription(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl">
      <ActionToast toast={toast} onDismiss={() => setToast(null)} />
      <h1 className="mb-8 text-2xl font-bold" style={{ color: "var(--color-text)" }}>Settings</h1>

      {loadError ? (
        <div className="rounded-lg p-5" style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)" }} role="alert">
          <h2 className="mb-2 text-base font-semibold text-red-500">Settings unavailable</h2>
          <p className="mb-4 text-sm" style={{ color: "var(--color-text-secondary)" }}>{loadError}</p>
          <button type="button" onClick={() => window.location.reload()} className="btn-secondary">Retry</button>
        </div>
      ) : (
        <div className="space-y-6">
          <SettingsSection title="Profile">
            <form onSubmit={handleProfileSave} className="grid max-w-2xl grid-cols-1 gap-4 md:grid-cols-2">
              <input value={profile.name} onChange={(event) => setProfile({ ...profile, name: event.target.value })} className="input-field" placeholder="Your name" disabled={savingProfile} />
              <input type="email" value={profile.email} onChange={(event) => setProfile({ ...profile, email: event.target.value })} className="input-field" required disabled={savingProfile} />
              <button type="submit" className="btn-primary md:col-span-2" disabled={savingProfile}>{savingProfile ? "Saving..." : "Save Profile"}</button>
            </form>
          </SettingsSection>

          <SettingsSection title="Subscription">
            <SubscriptionPanel profile={profile} trialDaysLeft={trialDaysLeft} onManage={handleManageSubscription} busy={managingSubscription} />
          </SettingsSection>

          <SettingsSection title="Connections" description={`Forward fallback: ${invoiceSettings.forward_address || "not generated yet"}`}>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {connectionRows.map((row) => {
                const connected = Boolean(invoiceSettings.connections[row.id as keyof InvoiceSettings["connections"]]);
                return (
                  <div key={row.id} className="flex items-center justify-between gap-4 rounded-lg p-4" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                    <div className="flex items-center gap-3">
                      <row.icon size={18} style={{ color: connected ? "#059669" : "var(--color-text-secondary)" }} />
                      <div>
                        <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>{row.label}</p>
                        <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{row.detail}</p>
                      </div>
                    </div>
                    <div className="flex min-w-0 flex-col items-end gap-2">
                      {row.id === "stripe" ? (
                        <input
                          type="password"
                          value={paymentCredentials.stripe_api_key}
                          onChange={(event) => setPaymentCredentials((current) => ({ ...current, stripe_api_key: event.target.value }))}
                          className="input-field h-9 w-44 text-xs"
                          placeholder="Restricted key"
                          autoComplete="off"
                        />
                      ) : null}
                      {row.id === "paypal" ? (
                        <div className="flex flex-col gap-2">
                          <input
                            type="password"
                            value={paymentCredentials.paypal_client_id}
                            onChange={(event) => setPaymentCredentials((current) => ({ ...current, paypal_client_id: event.target.value }))}
                            className="input-field h-9 w-44 text-xs"
                            placeholder="Client ID"
                            autoComplete="off"
                          />
                          <input
                            type="password"
                            value={paymentCredentials.paypal_client_secret}
                            onChange={(event) => setPaymentCredentials((current) => ({ ...current, paypal_client_secret: event.target.value }))}
                            className="input-field h-9 w-44 text-xs"
                            placeholder="Client secret"
                            autoComplete="off"
                          />
                        </div>
                      ) : null}
                      <button type="button" onClick={() => handleConnect(row.id)} className="btn-secondary flex items-center gap-2 px-3 py-2 text-sm" disabled={connecting === row.id}>
                        {connected ? <CheckCircle2 size={14} /> : connecting === row.id ? <RefreshCw size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                        {connected ? "Connected" : "Connect"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </SettingsSection>

          <SettingsSection title="Reminder Settings" description="Configure sender escalation, safe send windows, and notifications.">
            <form onSubmit={handleSettingsSave} className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <input className="input-field" placeholder="Company name" value={invoiceSettings.company_name} onChange={(event) => setInvoiceSettings({ ...invoiceSettings, company_name: event.target.value })} />
              <input className="input-field" placeholder="Sender name" value={invoiceSettings.sender_name} onChange={(event) => setInvoiceSettings({ ...invoiceSettings, sender_name: event.target.value })} />
              <input className="input-field" placeholder="Timezone" value={invoiceSettings.timezone} onChange={(event) => setInvoiceSettings({ ...invoiceSettings, timezone: event.target.value })} />
              <label className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
                Send hour
                <input className="input-field mt-1 w-full" type="number" min={0} max={23} value={invoiceSettings.send_hour} onChange={(event) => setInvoiceSettings({ ...invoiceSettings, send_hour: Number(event.target.value) })} />
              </label>
              <label className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
                Do not send after
                <input className="input-field mt-1 w-full" type="number" min={0} max={23} value={invoiceSettings.no_send_after_hour} onChange={(event) => setInvoiceSettings({ ...invoiceSettings, no_send_after_hour: Number(event.target.value) })} />
              </label>
              <div className="space-y-3 rounded-lg p-3" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                <label className="flex items-center gap-2 text-sm" style={{ color: "var(--color-text)" }}>
                  <input type="checkbox" checked={invoiceSettings.skip_weekends} onChange={(event) => setInvoiceSettings({ ...invoiceSettings, skip_weekends: event.target.checked })} />
                  No weekends
                </label>
                <label className="flex items-center gap-2 text-sm" style={{ color: "var(--color-text)" }}>
                  <input type="checkbox" checked={invoiceSettings.weekly_digest_enabled} onChange={(event) => setInvoiceSettings({ ...invoiceSettings, weekly_digest_enabled: event.target.checked })} />
                  Weekly digest
                </label>
                <label className="flex items-center gap-2 text-sm" style={{ color: "var(--color-text)" }}>
                  <input type="checkbox" checked={invoiceSettings.immediate_alerts_enabled} onChange={(event) => setInvoiceSettings({ ...invoiceSettings, immediate_alerts_enabled: event.target.checked })} />
                  Immediate alerts
                </label>
              </div>
              <button type="submit" className="btn-primary flex items-center justify-center gap-2 md:col-span-3" disabled={savingSettings}>
                <Save size={14} />
                {savingSettings ? "Saving..." : "Save Reminder Settings"}
              </button>
            </form>
          </SettingsSection>

          <SettingsSection title="Templates" description="Edit sequence templates and preview variables before reminders are sent.">
            <div className="space-y-4">
              {templates.map((template) => (
                <div key={template.id} className="rounded-lg p-4" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                  <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Day {template.day}: {template.name}</p>
                      <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{template.tone}</p>
                    </div>
                    <label className="flex items-center gap-2 text-sm" style={{ color: "var(--color-text)" }}>
                      <input type="checkbox" checked={template.enabled} onChange={(event) => setTemplates((current) => current.map((item) => item.id === template.id ? { ...item, enabled: event.target.checked } : item))} />
                      Enabled
                    </label>
                  </div>
                  <input className="input-field mb-3 w-full" value={template.subject} onChange={(event) => setTemplates((current) => current.map((item) => item.id === template.id ? { ...item, subject: event.target.value } : item))} />
                  <textarea className="input-field h-28 w-full py-2" value={template.body} onChange={(event) => setTemplates((current) => current.map((item) => item.id === template.id ? { ...item, body: event.target.value } : item))} />
                  <div className="mt-3 rounded-lg p-3 text-sm" style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text-secondary)" }}>
                    {renderPreview(template, invoiceSettings)}
                  </div>
                  <button type="button" onClick={() => handleTemplateSave(template)} className="btn-secondary mt-3 flex items-center gap-2 px-3 py-2 text-sm" disabled={savingTemplateId === template.id}>
                    <Save size={14} />
                    {savingTemplateId === template.id ? "Saving..." : "Save Template"}
                  </button>
                </div>
              ))}
            </div>
          </SettingsSection>
        </div>
      )}
    </div>
  );
}
