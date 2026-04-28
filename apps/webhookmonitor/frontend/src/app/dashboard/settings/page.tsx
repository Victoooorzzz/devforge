"use client";
import { useState, useEffect } from "react";
import { apiClient, trackEvent } from "@devforge/core";

export default function SettingsPage() {
  const [profile, setProfile] = useState({ name: "", email: "", has_active_subscription: false });
  const [webhookSettings, setWebhookSettings] = useState({ forward_url: "" });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiClient.get("/auth/profile").then((r) => setProfile({
        name: r.data.name || "",
        email: r.data.email || "",
        has_active_subscription: r.data.has_active_subscription
      })),
      apiClient.get("/settings/webhook-prefs").then((r) => setWebhookSettings({
        forward_url: r.data.forward_url || ""
      }))
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

  const handleWebhookSave = async (e: React.FormEvent) => {
    e.preventDefault();
    trackEvent("settings_updated", { section: "webhook_prefs" });
    try {
      await apiClient.put("/settings/webhook-prefs", { forward_url: webhookSettings.forward_url });
      alert("Webhook preferences updated successfully");
    } catch (err: any) {
      alert("Failed to update preferences: " + (err.message));
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm("Are you sure you want to delete all webhook requests history? This cannot be undone.")) return;
    trackEvent("webhook_history_cleared");
    try {
      await apiClient.delete("/webhooks/requests");
      alert("History cleared successfully");
    } catch (err: any) {
      alert("Failed to clear history: " + err.message);
    }
  };

  const handleManageSubscription = async () => {
    trackEvent("subscription_manage_clicked");
    if (profile.has_active_subscription) {
      try {
        const { data } = await apiClient.get("/lemonsqueezy/portal");
        window.open(data.portal_url, "_blank");
      } catch (err) {
        alert("Failed to open portal");
      }
    } else {
      try {
        const { data } = await apiClient.post("/lemonsqueezy/checkout", { variant_id: "default" });
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
        <h2 className="text-lg font-semibold mb-4" style={{ color: "var(--color-text)" }}>Webhook Preferences</h2>
        <form onSubmit={handleWebhookSave} className="space-y-4 max-w-md mb-6">
          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Forward URL</label>
            <input 
              type="url"
              value={webhookSettings.forward_url} 
              onChange={(e) => setWebhookSettings({ ...webhookSettings, forward_url: e.target.value })} 
              className="input-field w-full" 
              placeholder="https://your-server.com/api/webhooks"
            />
            <p className="text-xs mt-1.5" style={{ color: "var(--color-text-secondary)" }}>Automatically forward incoming requests to this URL.</p>
          </div>
          <button type="submit" className="btn-primary">Save Preferences</button>
        </form>

        <div className="pt-6" style={{ borderTop: "1px solid var(--color-border)" }}>
          <h3 className="text-md font-medium mb-2 text-red-500">Danger Zone</h3>
          <p className="text-sm mb-4" style={{ color: "var(--color-text-secondary)" }}>Permanently delete all captured webhook requests.</p>
          <button onClick={handleClearHistory} className="px-4 py-2 bg-red-500/10 text-red-500 hover:bg-red-500/20 rounded-md font-medium text-sm transition-colors border border-red-500/20">
            Clear History
          </button>
        </div>
      </section>
    </div>
  );
}
