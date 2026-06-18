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

type InvoiceSettings = {
  email_template: string;
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
  const [invoiceSettings, setInvoiceSettings] = useState<InvoiceSettings>({ email_template: "" });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingInvoice, setSavingInvoice] = useState(false);
  const [managingSubscription, setManagingSubscription] = useState(false);
  const [toast, setToast] = useState<DashboardToast | null>(null);

  useEffect(() => {
    let mounted = true;

    async function loadSettings() {
      try {
        const [profileResponse, invoiceResponse] = await Promise.all([
          apiClient.get<Profile>("/auth/profile"),
          apiClient.get<InvoiceSettings>("/settings/invoice-template"),
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
        setInvoiceSettings({
          email_template: invoiceResponse.data.email_template || "",
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

  const handleInvoiceSave = async (event: FormEvent) => {
    event.preventDefault();
    if (savingInvoice) return;

    setSavingInvoice(true);
    trackEvent("settings_updated", { section: "invoice_template" });

    try {
      await apiClient.put("/settings/invoice-template", {
        email_template: invoiceSettings.email_template,
      });
      setToast({ tone: "success", message: "Invoice template updated successfully." });
    } catch (error) {
      setToast({
        tone: "error",
        message: getSettingsErrorMessage(error, "Failed to update invoice template."),
      });
    } finally {
      setSavingInvoice(false);
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
            title="Invoice Preferences"
            description="Customize the email body used for overdue invoice follow-ups."
          >
            <form onSubmit={handleInvoiceSave} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
                  Email Template
                </label>
                <textarea
                  value={invoiceSettings.email_template}
                  onChange={(event) => setInvoiceSettings({ email_template: event.target.value })}
                  className="input-field h-32 w-full py-2"
                  placeholder="Template for overdue invoices..."
                  required
                  disabled={savingInvoice}
                />
              </div>
              <button type="submit" className="btn-primary" disabled={savingInvoice}>
                {savingInvoice ? "Saving..." : "Save Preferences"}
              </button>
            </form>
          </SettingsSection>
        </>
      )}
    </div>
  );
}
