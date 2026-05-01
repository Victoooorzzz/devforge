"use client";
import { useState, useEffect } from "react";
import { apiClient, trackEvent } from "@devforge/core";
import { product } from "@/config/product";

export default function SettingsPage() {
  const [profile, setProfile] = useState({
    name: "", email: "", has_active_subscription: false,
    is_on_trial: false, has_access: false, trial_ends_at: null as string | null,
  });
  const [trackerSettings, setTrackerSettings] = useState({ alert_email: "", frequency: "24h" });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiClient.get("/auth/profile").then((r) => {
        const d = r.data as any;
        setProfile({ name: d.name||"", email: d.email||"", has_active_subscription: d.has_active_subscription, is_on_trial: d.is_on_trial, has_access: d.has_access, trial_ends_at: d.trial_ends_at });
      }),
      apiClient.get("/settings/tracker-prefs").then((r) => {
        const d = r.data as any;
        setTrackerSettings({ alert_email: d.alert_email||"", frequency: d.frequency||"24h" });
      })
    ]).finally(() => setLoading(false));
  }, []);

  const handleProfileSave = async (e: React.FormEvent) => { e.preventDefault(); trackEvent("settings_updated",{section:"profile"}); try { await apiClient.put("/auth/profile",{name:profile.name,email:profile.email}); alert("Profile updated successfully"); } catch(err:any){ alert("Failed: "+(err.response?.data?.detail||err.message)); }};
  const handleTrackerSave = async (e: React.FormEvent) => { e.preventDefault(); trackEvent("settings_updated",{section:"tracker_prefs"}); try { await apiClient.put("/settings/tracker-prefs",{alert_email:trackerSettings.alert_email,frequency:trackerSettings.frequency}); alert("Tracker preferences updated"); } catch(err:any){ alert("Failed: "+err.message); }};
  const handleManageSubscription = async () => { trackEvent("subscription_manage_clicked"); if(profile.has_active_subscription){ try{ const{data}=await apiClient.get("/lemonsqueezy/portal") as{data:{portal_url:string}}; window.open(data.portal_url,"_blank"); }catch{alert("Failed to open portal");} }else{ try{ const{data}=await apiClient.post("/lemonsqueezy/checkout",{variant_id:product.pricing.lsVariantId}) as{data:{checkout_url:string}}; window.open(data.checkout_url,"_blank"); }catch{alert("Failed to start checkout");} }};

  const trialDaysLeft = profile.trial_ends_at ? Math.max(0,Math.ceil((new Date(profile.trial_ends_at).getTime()-Date.now())/(1000*60*60*24))) : 0;
  if (loading) return <div className="p-8" style={{color:"var(--color-text-secondary)"}}>Loading settings...</div>;

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold tracking-tight mb-8" style={{color:"var(--color-text)"}}>Settings</h1>

      <section className="p-6 rounded-lg mb-8" style={{backgroundColor:"var(--color-surface)"}}>
        <h2 className="text-lg font-semibold mb-4" style={{color:"var(--color-text)"}}>Profile</h2>
        <form onSubmit={handleProfileSave} className="space-y-4 max-w-md">
          <div><label className="block text-sm font-medium mb-1.5" style={{color:"var(--color-text-secondary)"}}>Name</label><input value={profile.name} onChange={(e)=>setProfile({...profile,name:e.target.value})} className="input-field w-full" placeholder="Your name"/></div>
          <div><label className="block text-sm font-medium mb-1.5" style={{color:"var(--color-text-secondary)"}}>Email</label><input type="email" value={profile.email} onChange={(e)=>setProfile({...profile,email:e.target.value})} className="input-field w-full" required/></div>
          <button type="submit" className="btn-primary">Save Profile</button>
        </form>
      </section>

      <section className="p-6 rounded-lg mb-8" style={{backgroundColor:"var(--color-surface)"}}>
        <h2 className="text-lg font-semibold mb-4" style={{color:"var(--color-text)"}}>Subscription</h2>
        {profile.is_on_trial && !profile.has_active_subscription && (
          <div className="p-4 rounded-lg mb-4 border" style={{backgroundColor:"var(--color-accent-dim)",borderColor:"var(--color-accent)"}}>
            <div className="flex items-center gap-2 mb-1"><span className="text-lg">🎉</span><p className="text-sm font-semibold" style={{color:"var(--color-text)"}}>Free Trial Active</p></div>
            <p className="text-xs" style={{color:"var(--color-text-secondary)"}}>You have <strong style={{color:"var(--color-accent)"}}>{trialDaysLeft} day{trialDaysLeft!==1?"s":""}</strong> remaining. Subscribe now to keep access.</p>
          </div>
        )}
        {!profile.is_on_trial && !profile.has_active_subscription && profile.trial_ends_at && (
          <div className="p-4 rounded-lg mb-4 border" style={{backgroundColor:"rgba(239,68,68,0.1)",borderColor:"rgba(239,68,68,0.3)"}}>
            <div className="flex items-center gap-2 mb-1"><span className="text-lg">⏰</span><p className="text-sm font-semibold" style={{color:"var(--color-text)"}}>Trial Expired</p></div>
            <p className="text-xs" style={{color:"var(--color-text-secondary)"}}>Your free trial has ended. Subscribe to regain access.</p>
          </div>
        )}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium" style={{color:"var(--color-text)"}}>{profile.has_active_subscription?"Active Plan":profile.is_on_trial?"Free Trial":"No active subscription"}</p>
            <p className="text-xs mt-1" style={{color:"var(--color-text-secondary)"}}>{profile.has_active_subscription?"You are currently on a premium plan.":profile.is_on_trial?`Your trial ends on ${new Date(profile.trial_ends_at!).toLocaleDateString()}.`:"Subscribe to access all features."}</p>
          </div>
          <button onClick={handleManageSubscription} className="btn-primary">{profile.has_active_subscription?"Manage Plan":profile.is_on_trial?"Subscribe Now":"Subscribe"}</button>
        </div>
      </section>

      <section className="p-6 rounded-lg mb-8" style={{backgroundColor:"var(--color-surface)"}}>
        <h2 className="text-lg font-semibold mb-4" style={{color:"var(--color-text)"}}>Tracker Preferences</h2>
        <form onSubmit={handleTrackerSave} className="space-y-4 max-w-md">
          <div><label className="block text-sm font-medium mb-1.5" style={{color:"var(--color-text-secondary)"}}>Alert Email</label><input type="email" value={trackerSettings.alert_email} onChange={(e)=>setTrackerSettings({...trackerSettings,alert_email:e.target.value})} className="input-field w-full" placeholder="Email to receive price drop alerts" required/></div>
          <div><label className="block text-sm font-medium mb-1.5" style={{color:"var(--color-text-secondary)"}}>Check Frequency</label><select value={trackerSettings.frequency} onChange={(e)=>setTrackerSettings({...trackerSettings,frequency:e.target.value})} className="input-field w-full"><option value="12h">Every 12 Hours</option><option value="24h">Every 24 Hours</option></select></div>
          <button type="submit" className="btn-primary">Save Preferences</button>
        </form>
      </section>
    </div>
  );
}
