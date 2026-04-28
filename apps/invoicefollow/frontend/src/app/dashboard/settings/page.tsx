"use client";
import { useState, useEffect } from "react";
import { apiClient, trackEvent } from "@devforge/core";

export default function SettingsPage() {
  const [profile, setProfile] = useState({ name: "", email: "", has_active_subscription: false });
  const [invoiceSettings, setInvoiceSettings] = useState({ email_template: "" });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiClient.get("/auth/profile").then((r) => {
        const data = r.data as { name: string; email: string; has_active_subscription: boolean };
        setProfile({
          name: data.name || "",
          email: data.email || "",
          has_active_subscription: data.has_active_subscription
        });
      }),
      apiClient.get("/settings/invoice-template").then((r) => {
        const data = r.data as { email_template: string };
        setInvoiceSettings({
          email_template: data.email_template || ""
        });
      })
    ]).finally(() => setLoading(false));
  }, []);

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    trackEvent("settings_updated", { section: "profile" });
    try {
      await apiClient.put("/auth/profile", { name: profile.name, email: profile.email });
      alert("Profile updated successfully");
    } catch (err: any) {
      alert("Failed to update profile: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleInvoiceSave = async (e: React.FormEvent) => {
    e.preventDefault();
    trackEvent("settings_updated", { section: "invoice_template" });
    try {
      await apiClient.put("/settings/invoice-template", { email_template: invoiceSettings.email_template });
      alert("Invoice template updated successfully");
    } catch (err: any) {
      alert("Failed to update template: " + (err.message));
    }
  };

  const handleManageSubscription = async () => {
    trackEvent("subscription_manage_clicked");
    if (profile.has_active_subscription) {
      try {
        const { data } = await apiClient.get("/lemonsqueezy/portal") as { data: { portal_url: string } };
        window.open(data.portal_url, "_blank");
      } catch (err) {
        alert("Failed to open portal");
      }
    } else {
      try {
        const { data } = await apiClient.post("/lemonsqueezy/checkout", { variant_id: "default" }) as { data: { checkout_url: string } };
        window.open(data.checkout_url, "_blank");
      } catch (err) {
        alert("Failed to start checkout");
      }
    }
  };

  if (loading) return <div className="p-8" style={{ color: "var(--color-text-secondary)" }}>Loading settings...</div>;

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold tracking-tight mb-8" style={{ color: "var(--color-text)" }}>Settings</h1>

      <section className="p-6 rounded-lg mb-8" style={{ backgroundColor: "var(--color-surface)" }}>
        <h2 className="text-lg font-semibold mb-4" style={{ color: "var(--color-text)" }}>Profile</h2>
        <form onSubmit={handleProfileSave} className="space-y-4 max-w-md">
          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Name</label>
            <input value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} className="input-field w-full" placeholder="Your name" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Email</label>
            <input type="email" value={profile.email} onChange={(e) => setProfile({ ...profile, email: e.target.value })} className="input-field w-full" required />
          </div>
          <button type="submit" className="btn-primary">Save Profile</button>
        </form>
      </section>

      <section className="p-6 rounded-lg mb-8" style={{ backgroundColor: "var(--color-surface)" }}>
        <h2 className="text-lg font-semibold mb-4" style={{ color: "var(--color-text)" }}>Subscription</h2>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium" style={{ color: "var(--color-text)" }}>
              {profile.has_active_subscription ? "Active Plan" : "No active subscription"}
            </p>
            <p className="text-xs mt-1" style={{ color: "var(--color-text-secondary)" }}>
              {profile.has_active_subscription ? "You are currently on a premium plan." : "Subscribe to access all features."}
            </p>
          </div>
          <button onClick={handleManageSubscription} className="btn-primary">
            {profile.has_active_subscription ? "Manage Plan" : "Subscribe"}
          </button>
        </div>
      </section>

      <section className="p-6 rounded-lg mb-8" style={{ backgroundColor: "var(--color-surface)" }}>
        <h2 className="text-lg font-semibold mb-4" style={{ color: "var(--color-text)" }}>Invoice Preferences</h2>
        <form onSubmit={handleInvoiceSave} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Email Template</label>
            <textarea 
              value={invoiceSettings.email_template} 
              onChange={(e) => setInvoiceSettings({ ...invoiceSettings, email_template: e.target.value })} 
              className="input-field w-full h-32 py-2" 
              placeholder="Template for overdue invoices..." 
              required 
            />
          </div>
          <button type="submit" className="btn-primary">Save Preferences</button>
        </form>
      </section>
    </div>
  );
}
