"use client";
import { useState, useEffect } from "react";
import { apiClient, trackEvent } from "@devforge/core";

export default function SettingsPage() {
  const [profile, setProfile] = useState({ name: "", email: "", has_active_subscription: false });
  const [feedbackSettings, setFeedbackSettings] = useState({ custom_prompt: "", negative_threshold: 0.5 });
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
      apiClient.get("/settings/feedback-prefs").then((r) => {
        const data = r.data as { custom_prompt: string; negative_threshold: number };
        setFeedbackSettings({
          custom_prompt: data.custom_prompt || "",
          negative_threshold: data.negative_threshold ?? 0.5
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

  const handleFeedbackSave = async (e: React.FormEvent) => {
    e.preventDefault();
    trackEvent("settings_updated", { section: "feedback_prefs" });
    try {
      await apiClient.put("/settings/feedback-prefs", { 
        custom_prompt: feedbackSettings.custom_prompt,
        negative_threshold: Number(feedbackSettings.negative_threshold)
      });
      alert("Feedback preferences updated successfully");
    } catch (err: any) {
      alert("Failed to update preferences: " + (err.message));
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
        <h2 className="text-lg font-semibold mb-4" style={{ color: "var(--color-text)" }}>AI Analysis Preferences</h2>
        <form onSubmit={handleFeedbackSave} className="space-y-6 max-w-2xl">
          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Custom Prompt</label>
            <textarea 
              value={feedbackSettings.custom_prompt} 
              onChange={(e) => setFeedbackSettings({ ...feedbackSettings, custom_prompt: e.target.value })} 
              className="input-field w-full h-32 py-3" 
              placeholder="e.g. Focus specifically on pricing complaints and feature requests..."
            />
            <p className="text-xs mt-1.5" style={{ color: "var(--color-text-secondary)" }}>Additional instructions for the Gemini AI when analyzing feedback.</p>
          </div>
          <div>
            <div className="flex justify-between mb-1.5">
              <label className="block text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>Negative Threshold</label>
              <span className="text-sm font-medium" style={{ color: "var(--color-text)" }}>{feedbackSettings.negative_threshold}</span>
            </div>
            <input 
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={feedbackSettings.negative_threshold} 
              onChange={(e) => setFeedbackSettings({ ...feedbackSettings, negative_threshold: parseFloat(e.target.value) })} 
              className="w-full accent-[var(--color-primary)]" 
            />
            <p className="text-xs mt-1.5" style={{ color: "var(--color-text-secondary)" }}>Sentiment score below this value will be flagged as negative (0.0 to 1.0).</p>
          </div>
          <button type="submit" className="btn-primary">Save AI Preferences</button>
        </form>
      </section>
    </div>
  );
}
