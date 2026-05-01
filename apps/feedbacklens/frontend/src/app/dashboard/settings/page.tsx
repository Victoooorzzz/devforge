"use client";
import { useState, useEffect } from "react";
import { apiClient, trackEvent } from "@devforge/core";
import { product } from "@/config/product";

export default function SettingsPage() {
  const [profile, setProfile] = useState({
    name: "",
    email: "",
    has_active_subscription: false,
    is_on_trial: false,
    has_access: false,
    trial_ends_at: null as string | null,
  });
  const [feedbackSettings, setFeedbackSettings] = useState({ custom_prompt: "", negative_threshold: 0.5 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiClient.get("/auth/profile").then((r) => {
        const data = r.data as {
          name: string;
          email: string;
          has_active_subscription: boolean;
          is_on_trial: boolean;
          has_access: boolean;
          trial_ends_at: string | null;
        };
        setProfile({
          name: data.name || "",
          email: data.email || "",
          has_active_subscription: data.has_active_subscription,
          is_on_trial: data.is_on_trial,
          has_access: data.has_access,
          trial_ends_at: data.trial_ends_at,
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
        const { data } = await apiClient.post("/lemonsqueezy/checkout", { 
          variant_id: product.pricing.lsVariantId 
        }) as { data: { checkout_url: string } };
        window.open(data.checkout_url, "_blank");
      } catch (err) {
        alert("Failed to start checkout");
      }
    }
  };

  const trialDaysLeft = profile.trial_ends_at
    ? Math.max(0, Math.ceil((new Date(profile.trial_ends_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24)))
    : 0;

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

        {profile.is_on_trial && !profile.has_active_subscription && (
          <div className="p-4 rounded-lg mb-4 border" style={{ backgroundColor: "var(--color-accent-dim)", borderColor: "var(--color-accent)" }}>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">🎉</span>
              <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Free Trial Active</p>
            </div>
            <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>
              You have <strong style={{ color: "var(--color-accent)" }}>{trialDaysLeft} day{trialDaysLeft !== 1 ? "s" : ""}</strong> remaining.
              Subscribe now to keep access when your trial ends.
            </p>
          </div>
        )}

        {!profile.is_on_trial && !profile.has_active_subscription && profile.trial_ends_at && (
          <div className="p-4 rounded-lg mb-4 border" style={{ backgroundColor: "rgba(239, 68, 68, 0.1)", borderColor: "rgba(239, 68, 68, 0.3)" }}>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">⏰</span>
              <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Trial Expired</p>
            </div>
            <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>
              Your free trial has ended. Subscribe to regain access to all features.
            </p>
          </div>
        )}

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium" style={{ color: "var(--color-text)" }}>
              {profile.has_active_subscription
                ? "Active Plan"
                : profile.is_on_trial
                  ? "Free Trial"
                  : "No active subscription"}
            </p>
            <p className="text-xs mt-1" style={{ color: "var(--color-text-secondary)" }}>
              {profile.has_active_subscription
                ? "You are currently on a premium plan."
                : profile.is_on_trial
                  ? `Your trial ends on ${new Date(profile.trial_ends_at!).toLocaleDateString()}.`
                  : "Subscribe to access all features."}
            </p>
          </div>
          <button onClick={handleManageSubscription} className="btn-primary">
            {profile.has_active_subscription
              ? "Manage Plan"
              : profile.is_on_trial
                ? "Subscribe Now"
                : "Subscribe"}
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
