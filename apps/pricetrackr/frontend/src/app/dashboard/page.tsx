"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { apiClient, downloadFile, trackEvent } from "@devforge/core";
import {
  ActionToast,
  DashboardEmptyState,
  DashboardSkeleton,
  InlineErrorState,
  InlineSpinner,
  WelcomeSteps,
  type DashboardToast,
} from "@devforge/ui";
import { Download, ChevronDown, Bell, BellOff, Send, Loader2, X, Check } from "lucide-react";

interface TrackedUrl {
  id: number;
  url: string;
  label: string;
  current_price: number | null;
  previous_price: number | null;
  min_price: number | null;
  in_stock: boolean | null;
  last_checked: string | null;
  check_frequency_hours: number;
  status: string;
}

interface PricePoint {
  price: number | null;
  in_stock: boolean | null;
  recorded_at: string;
}

type ExportFormat = "csv" | "xlsx" | "json";

interface AlertConfig {
  threshold: string;
  open: boolean;
  saving: boolean;
  testing: boolean;
  saved: boolean;
}

interface TrackerSummary {
  total_trackers: number;
  active_trackers: number;
  price_drop_count: number;
  out_of_stock_count: number;
  potential_savings: number;
}

interface TrackerHealth {
  id: number;
  label: string;
  health: "healthy" | "stale" | "never_checked" | "price_missing" | "out_of_stock";
  severity: "ok" | "warning" | "critical";
  detail: string;
  last_checked: string | null;
  check_frequency_hours: number;
}

export default function DashboardPage() {
  const [trackers, setTrackers]   = useState<TrackedUrl[]>([]);
  const [showForm, setShowForm]   = useState(false);
  const [selected, setSelected]  = useState<TrackedUrl | null>(null);
  const [history, setHistory]     = useState<PricePoint[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [deleting, setDeleting]   = useState<Set<number>>(new Set());
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [form, setForm]           = useState({ url: "", label: "", check_frequency_hours: 24 });
  const [exportOpen, setExportOpen] = useState(false);
  const [alertConfigs, setAlertConfigs] = useState<Record<number, AlertConfig>>({});
  const [summary, setSummary] = useState<TrackerSummary | null>(null);
  const [health, setHealth] = useState<TrackerHealth[]>([]);
  const [savingTracker, setSavingTracker] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [toast, setToast] = useState<DashboardToast | null>(null);
  const exportRef = useRef<HTMLDivElement>(null);

  const showToast = useCallback((nextToast: DashboardToast) => {
    setToast(nextToast);
    window.setTimeout(() => setToast(null), 4500);
  }, []);

  const refreshTrackers = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    const [trackerResult, summaryResult, healthResult] = await Promise.allSettled([
      apiClient.get<TrackedUrl[]>("/trackers/list"),
      apiClient.get<TrackerSummary>("/trackers/summary"),
      apiClient.get<TrackerHealth[]>("/trackers/health"),
    ]);

    if (trackerResult.status === "fulfilled") setTrackers(trackerResult.value.data);
    if (summaryResult.status === "fulfilled") setSummary(summaryResult.value.data);
    if (healthResult.status === "fulfilled") setHealth(healthResult.value.data);
    if (trackerResult.status === "rejected" && summaryResult.status === "rejected" && healthResult.status === "rejected") {
      setLoadError(true);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    refreshTrackers();
  }, [refreshTrackers]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) setExportOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingTracker(true);
    trackEvent("feature_used", { feature_name: "add_tracker" });
    try {
      const { data } = await apiClient.post<TrackedUrl>("/trackers", { url: form.url, label: form.label, check_frequency_hours: form.check_frequency_hours });
      setTrackers(prev => [data, ...prev]);
      setForm({ url: "", label: "", check_frequency_hours: 24 });
      setShowForm(false);
      showToast({ tone: "success", message: `${data.label} is now being watched for price drops.` });
      refreshTrackers();
    } catch {
      showToast({ tone: "error", message: "We could not watch that product. Check the URL and try again." });
    } finally {
      setSavingTracker(false);
    }
  };

  const handleUpdateFrequency = async (id: number, hours: number) => {
    try {
      await apiClient.patch(`/trackers/${id}/frequency`, { hours });
      setTrackers(prev => prev.map(t => t.id === id ? { ...t, check_frequency_hours: hours } : t));
      showToast({ tone: "success", message: `We will check this product every ${hours}h.` });
    } catch {
      showToast({ tone: "error", message: "We could not update the check frequency. Retry from the product row." });
    }
  };

  const handleDelete = async (id: number) => {
    if (deleteConfirmId !== id) {
      setDeleteConfirmId(id);
      showToast({ tone: "info", message: "Click Stop watching again to remove this product." });
      window.setTimeout(() => setDeleteConfirmId(current => current === id ? null : current), 5000);
      return;
    }
    setDeleteConfirmId(null);
    setDeleting(prev => new Set(prev).add(id));
    try {
      await apiClient.delete(`/trackers/${id}`);
      setTrackers(prev => prev.filter(t => t.id !== id));
      if (selected?.id === id) setSelected(null);
      showToast({ tone: "success", message: "This product is no longer being watched." });
    } catch {
      showToast({ tone: "error", message: "We could not stop watching this product. Retry from the product row." });
    }
    finally { setDeleting(prev => { const s = new Set(prev); s.delete(id); return s; }); }
  };

  const handleSelect = async (t: TrackedUrl) => {
    setSelected(t);
    setLoadingHistory(true);
    trackEvent("feature_used", { feature_name: "view_price_history" });
    try {
      const { data } = await apiClient.get<PricePoint[]>(`/trackers/${t.id}/history`);
      setHistory(data);
    } catch {
      setHistory([]);
      showToast({ tone: "error", message: "We could not load this price history. Select the product again to retry." });
    }
    finally { setLoadingHistory(false); }
  };

  // Export — Skill: react-patterns
  const handleExport = async (format: ExportFormat) => {
    setExportOpen(false);
    trackEvent("feature_used", { feature_name: "export_trackers", format });
    try {
      await downloadFile(`/trackers/export?format=${format}`, `pricetrackr_export.${format}`);
      showToast({ tone: "success", message: `Your watched products export started as ${format.toUpperCase()}.` });
    } catch {
      showToast({ tone: "error", message: "We could not export your watched products. Retry from the export menu." });
    }
  };

  // Alert threshold config — Skill: backend-architect
  const toggleAlertPanel = (id: number) => {
    setAlertConfigs(prev => ({
      ...prev,
      [id]: prev[id]?.open 
        ? { ...prev[id], open: false }
        : { threshold: "", open: true, saving: false, testing: false, saved: false }
    }));
  };

  const handleSaveAlert = async (id: number) => {
    const cfg = alertConfigs[id];
    if (!cfg?.threshold) return;
    setAlertConfigs(prev => ({ ...prev, [id]: { ...prev[id], saving: true, saved: false } }));
    trackEvent("feature_used", { feature_name: "set_price_alert" });
    try {
      await apiClient.patch(`/trackers/${id}/alert-threshold`, {
        alert_threshold: parseFloat(cfg.threshold)
      });
      setAlertConfigs(prev => ({ ...prev, [id]: { ...prev[id], saving: false, saved: true, open: false } }));
      showToast({ tone: "success", message: "Price alert saved. We will email you when the price drops." });
      setTimeout(() => setAlertConfigs(prev => ({ ...prev, [id]: { ...prev[id], saved: false } })), 3000);
    } catch {
      setAlertConfigs(prev => ({ ...prev, [id]: { ...prev[id], saving: false } }));
      showToast({ tone: "error", message: "We could not save this price alert. Check the amount and retry." });
    }
  };

  const handleTestAlert = async (id: number) => {
    setAlertConfigs(prev => ({ ...prev, [id]: { ...(prev[id] || { threshold: "", open: false, saving: false, saved: false }), testing: true } }));
    trackEvent("feature_used", { feature_name: "test_price_alert" });
    try {
      await apiClient.post(`/trackers/${id}/test-alert`, {});
      showToast({ tone: "success", message: "Test price alert email sent." });
    } catch {
      showToast({ tone: "error", message: "We could not send the test alert. Check your alert email in settings." });
    }
    finally { setAlertConfigs(prev => ({ ...prev, [id]: { ...prev[id], testing: false } })); }
  };

  const priceDiff = (t: TrackedUrl) => {
    if (!t.current_price || !t.previous_price) return null;
    return ((t.current_price - t.previous_price) / t.previous_price) * 100;
  };

  const safeNumber = (value: unknown, fallback = 0) =>
    typeof value === "number" && Number.isFinite(value) ? value : fallback;
  const formatCount = (value: unknown, fallback = 0) => safeNumber(value, fallback).toLocaleString();
  const formatMoney = (value: unknown) => `$${safeNumber(value).toFixed(2)}`;

  const isMinHistoric = (t: TrackedUrl) =>
    t.current_price !== null && t.min_price !== null && t.current_price <= t.min_price;

  const Sparkline = ({ points }: { points: PricePoint[] }) => {
    const prices = points.map(p => p.price).filter(Boolean) as number[];
    if (prices.length < 2) return <span className="text-xs" style={{ color: "var(--color-text-secondary)" }}>No price history yet</span>;
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || 1;
    const w = 120; const h = 32;
    const pts = prices.map((p, i) => `${(i / (prices.length - 1)) * w},${h - ((p - min) / range) * h}`).join(" ");
    return (
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
        <polyline fill="none" stroke="var(--color-accent)" strokeWidth="1.5" points={pts} />
      </svg>
    );
  };

  return (
    <div className="flex gap-6">
      <ActionToast toast={toast} onDismiss={() => setToast(null)} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "var(--color-text)" }}>Products you watch</h1>
            <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{trackers.length} products watched for price drops</p>
          </div>
          <div className="flex items-center gap-2">
            {/* Export dropdown */}
            <div className="relative" ref={exportRef}>
              <button onClick={() => setExportOpen(!exportOpen)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all"
                style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)" }}>
                <Download size={14} />
                <span>Export watched products</span>
                <ChevronDown size={12} className={`transition-transform ${exportOpen ? "rotate-180" : ""}`} />
              </button>
              {exportOpen && (
                <div className="absolute right-0 top-full mt-2 w-44 rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200"
                  style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                  {(["csv", "xlsx", "json"] as ExportFormat[]).map(f => (
                    <button key={f} onClick={() => handleExport(f)}
                      className="w-full text-left px-4 py-2.5 text-sm hover:bg-black/5 transition-colors"
                      style={{ color: "var(--color-text)" }}>
                    {f.toUpperCase()} - {f === "csv" ? "Spreadsheet" : f === "xlsx" ? "Excel" : "JSON"}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button onClick={() => setShowForm(!showForm)} className="btn-primary">Watch product</button>
          </div>
        </div>

        {loadError && (
          <div className="mb-6">
            <InlineErrorState
              title="We could not load your watched products"
              description="Your product list did not load. Retry now, and contact support if it keeps happening."
              onRetry={refreshTrackers}
            />
          </div>
        )}

        {loading && trackers.length === 0 && <DashboardSkeleton rows={4} />}

        {!loading && !loadError && trackers.length === 0 && (
          <WelcomeSteps
            title="Watch your first product"
            description="Track price drops, back-in-stock changes, and potential savings from one product URL."
            steps={[
              "Paste a product URL and give it a clear name.",
              "Choose how often we should check for price changes.",
              "Add an alert so you hear when the price drops.",
            ]}
            actionLabel="Watch your first product"
            onAction={() => setShowForm(true)}
          />
        )}

        {!loading && (
        <>
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {[
              { label: "Products watched", value: formatCount(summary.active_trackers, trackers.length), color: "var(--color-accent)" },
              { label: "Dropped in price", value: formatCount(summary.price_drop_count), color: "#10B981" },
              { label: "Out of stock", value: formatCount(summary.out_of_stock_count), color: safeNumber(summary.out_of_stock_count) ? "#EF4444" : "#10B981" },
              { label: "Potential savings", value: formatMoney(summary.potential_savings), color: "#F59E0B" },
            ].map(stat => (
              <div key={stat.label} className="p-4 rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
                <p className="text-xs mb-1" style={{ color: "var(--color-text-secondary)" }}>{stat.label}</p>
                <p className="text-xl font-bold font-mono" style={{ color: stat.color }}>{stat.value}</p>
              </div>
            ))}
          </div>
        )}

        {health.length > 0 && (
          <div className="mb-6 p-4 rounded-lg" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="flex items-center justify-between gap-4 mb-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider opacity-50">Price check health</p>
                <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>Products needing attention are listed first.</p>
              </div>
              <span className="text-xs font-mono" style={{ color: "var(--color-text-secondary)" }}>
                {health.filter(item => item.severity !== "ok").length} issues
              </span>
            </div>
            <div className="space-y-2">
              {health.slice(0, 4).map(item => (
                <div key={item.id} className="flex items-start justify-between gap-3 p-3 rounded-md" style={{ backgroundColor: "rgba(0,0,0,0.04)" }}>
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: "var(--color-text)" }}>{item.label}</p>
                    <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{item.detail}</p>
                  </div>
                  <span className={`text-[10px] font-bold uppercase px-2 py-1 rounded ${
                    item.severity === "critical" ? "bg-red-500/10 text-red-500" :
                    item.severity === "warning" ? "bg-amber-500/10 text-amber-500" :
                    "bg-emerald-500/10 text-emerald-500"
                  }`}>
                    {item.health.replace("_", " ")}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {showForm && (
          <form onSubmit={handleAdd} className="p-6 rounded-lg mb-6 grid grid-cols-1 md:grid-cols-3 gap-4 items-end"
            style={{ backgroundColor: "var(--color-surface)" }}>
            <div className="md:col-span-1">
              <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Product name</label>
              <input value={form.label} onChange={e => setForm({ ...form, label: e.target.value })} className="input-field" placeholder="Example: iPhone 15 Pro" required />
            </div>
            <div className="md:col-span-1">
              <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Product URL</label>
              <input type="url" value={form.url} onChange={e => setForm({ ...form, url: e.target.value })} className="input-field" placeholder="https://..." required />
            </div>
            <div className="md:col-span-1 flex items-end gap-3">
              <div className="flex-1">
                <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Check every</label>
                <select value={form.check_frequency_hours} onChange={e => setForm({ ...form, check_frequency_hours: parseInt(e.target.value) })} className="input-field cursor-pointer px-3">
                  <option value={1}>Every 1h</option>
                  <option value={6}>Every 6h</option>
                  <option value={12}>Every 12h</option>
                  <option value={24}>Every 24h</option>
                </select>
              </div>
              <button type="submit" disabled={savingTracker} className="btn-primary flex-1">
                {savingTracker ? <InlineSpinner /> : null}
                {savingTracker ? "Watching product" : "Watch product"}
              </button>
            </div>
          </form>
        )}

        <div className="space-y-3">
          {trackers.length === 0 && (
            <DashboardEmptyState
              icon={<Bell size={24} />}
              title="Watch your first product"
              description="Add a product URL to see when it drops in price, comes back in stock, or reaches a new low."
              actionLabel="Watch a product"
              onAction={() => setShowForm(true)}
            />
          )}
          {trackers.map(t => {
            const diff = priceDiff(t);
            const isMin = isMinHistoric(t);
            const alertCfg = alertConfigs[t.id];
            return (
              <div key={t.id} className="rounded-lg overflow-hidden" style={{ backgroundColor: selected?.id === t.id ? "var(--color-surface-raised)" : "var(--color-surface)", border: isMin ? "1px solid rgba(16,185,129,0.4)" : "1px solid transparent" }}>
                <div onClick={() => handleSelect(t)} className="p-4 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 cursor-pointer">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <p className="text-sm font-semibold truncate" style={{ color: "var(--color-text)" }}>{t.label}</p>
                      {isMin && (
                        <span className="text-xs font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: "rgba(16,185,129,0.15)", color: "#10B981" }}>NEW LOW</span>
                      )}
                      {t.in_stock === false && (
                        <span className="text-xs font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: "rgba(239,68,68,0.15)", color: "#EF4444" }}>OUT OF STOCK</span>
                      )}
                      {/* Alert configured badge */}
                      {alertCfg?.saved && (
                        <span className="text-xs font-bold px-2 py-0.5 rounded-full flex-shrink-0 animate-in fade-in"
                          style={{ backgroundColor: "rgba(99,102,241,0.15)", color: "#6366F1" }}>
                          <Bell size={10} className="inline mr-1" />ALERT SAVED
                        </span>
                      )}
                    </div>
                    <p className="text-xs truncate" style={{ color: "var(--color-text-secondary)" }}>{t.url}</p>
                  </div>
                  <div className="w-full sm:w-auto flex flex-wrap items-center gap-2 sm:gap-3 sm:flex-shrink-0">
                    <div className="min-w-[90px] text-left sm:text-right mr-auto sm:mr-0">
                      {t.current_price !== null ? (
                        <p className="text-lg font-bold font-mono" style={{ color: "var(--color-accent)" }}>
                          ${t.current_price.toFixed(2)}
                        </p>
                      ) : (
                        <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>No price yet</p>
                      )}
                      {diff !== null && (
                        <p className="text-xs font-mono" style={{ color: diff < 0 ? "#10B981" : "#EF4444" }}>
                          {diff < 0 ? "▼" : "▲"} {Math.abs(diff).toFixed(1)}%
                        </p>
                      )}
                    </div>
                    {/* Frequency selector */}
                    <select
                      value={t.check_frequency_hours}
                      onChange={e => handleUpdateFrequency(t.id, parseInt(e.target.value))}
                      onClick={e => e.stopPropagation()}
                      className="text-xs px-2 py-1.5 rounded border-0 outline-none cursor-pointer transition-colors"
                      style={{ backgroundColor: "var(--color-surface-high)", color: "var(--color-text-secondary)" }}
                      title="How often we check this product"
                    >
                      <option value={1}>1h</option>
                      <option value={6}>6h</option>
                      <option value={12}>12h</option>
                      <option value={24}>24h</option>
                    </select>

                    {/* Alert button */}
                    <button
                      onClick={e => { e.stopPropagation(); toggleAlertPanel(t.id); }}
                      className="p-2 rounded-lg transition-colors"
                      style={{
                        backgroundColor: alertCfg?.open ? "rgba(99,102,241,0.1)" : "var(--color-surface-high)",
                        color: alertCfg?.open ? "#6366F1" : "var(--color-text-secondary)"
                      }}
                      title="Save a price drop alert"
                    >
                      {alertCfg?.saved ? <Bell size={16} /> : <BellOff size={16} />}
                    </button>
                    <button onClick={e => { e.stopPropagation(); handleDelete(t.id); }}
                      disabled={deleting.has(t.id)}
                      className="text-xs px-2 py-1 rounded transition-colors whitespace-nowrap"
                      style={{ backgroundColor: "var(--color-surface-high)", color: "var(--color-text-secondary)" }}>
                      {deleting.has(t.id) ? "Removing" : "Stop watching"}
                    </button>
                  </div>
                </div>

                {/* Alert configuration panel */}
                {alertCfg?.open && (
                  <div className="px-4 pb-4 border-t border-[var(--color-border)] pt-3 animate-in fade-in slide-in-from-top-2 duration-200">
                    <p className="text-xs font-medium mb-2 flex items-center gap-1.5"
                      style={{ color: "var(--color-text-secondary)" }}>
                      <Bell size={12} /> Alert me when the price drops below:
                    </p>
                    <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                      <div className="relative flex-1 min-w-[160px]">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-mono"
                          style={{ color: "var(--color-text-secondary)" }}>$</span>
                        <input
                          type="number" step="0.01" min="0"
                          value={alertCfg.threshold}
                          onChange={e => setAlertConfigs(prev => ({ ...prev, [t.id]: { ...prev[t.id], threshold: e.target.value } }))}
                          className="input-field pl-7 text-sm"
                          placeholder={t.current_price ? (t.current_price * 0.9).toFixed(2) : "0.00"}
                        />
                      </div>
                      <button onClick={() => handleSaveAlert(t.id)}
                        disabled={alertCfg.saving || !alertCfg.threshold}
                        className="px-3 py-2 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-1.5"
                        style={{ backgroundColor: "var(--color-primary)", color: "#000", opacity: alertCfg.saving || !alertCfg.threshold ? 0.6 : 1 }}>
                        {alertCfg.saving ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
                        Save alert
                      </button>
                      <button onClick={() => handleTestAlert(t.id)}
                        disabled={alertCfg.testing}
                        className="px-3 py-2 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-1.5"
                        style={{ backgroundColor: "var(--color-surface-high)", color: "var(--color-text)" }}>
                        {alertCfg.testing ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                        Test
                      </button>
                      <button onClick={() => toggleAlertPanel(t.id)}
                        className="p-2 rounded-lg hover:bg-black/5 transition-colors"
                        style={{ color: "var(--color-text-secondary)" }}>
                        <X size={14} />
                      </button>
                    </div>
                    <p className="text-[10px] mt-2" style={{ color: "var(--color-text-secondary)" }}>
                      We will email you when the detected price is below your saved amount.
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
        </>
        )}
      </div>

      {/* History sidebar */}
      {selected && (
        <div className="w-80 flex-shrink-0 rounded-lg p-4" style={{ backgroundColor: "var(--color-surface)" }}>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold truncate" style={{ color: "var(--color-text)" }}>{selected.label}</p>
            <button onClick={() => setSelected(null)} className="text-xs" style={{ color: "var(--color-text-secondary)" }}>Close</button>
          </div>
          {loadingHistory ? (
            <p className="text-xs text-center py-8" style={{ color: "var(--color-text-secondary)" }}>Loading price history...</p>
          ) : history.length === 0 ? (
            <p className="text-xs text-center py-8" style={{ color: "var(--color-text-secondary)" }}>No price history yet. The first check runs in the next few hours.</p>
          ) : (
            <div className="space-y-4">
              <div>
                <p className="text-xs font-medium mb-2 uppercase tracking-wide" style={{ color: "var(--color-text-secondary)" }}>Price movement</p>
                <Sparkline points={history} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Lowest price", value: selected.min_price ? `$${selected.min_price.toFixed(2)}` : "—", color: "#10B981" },
                  { label: "Current price", value: selected.current_price ? `$${selected.current_price.toFixed(2)}` : "—", color: "var(--color-accent)" },
                ].map(s => (
                  <div key={s.label} className="p-3 rounded-lg" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                    <p className="text-xs mb-1" style={{ color: "var(--color-text-secondary)" }}>{s.label}</p>
                    <p className="text-base font-bold font-mono" style={{ color: s.color }}>{s.value}</p>
                  </div>
                ))}
              </div>
              <div>
                <p className="text-xs font-medium mb-2 uppercase tracking-wide" style={{ color: "var(--color-text-secondary)" }}>Latest checks</p>
                <div className="space-y-1 max-h-48 overflow-auto">
                  {history.slice(0, 20).map((p, i) => (
                    <div key={i} className="flex justify-between text-xs py-1" style={{ borderBottom: "1px solid rgba(38,38,38,0.3)" }}>
                      <span style={{ color: "var(--color-text-secondary)" }}>{new Date(p.recorded_at).toLocaleDateString("es-PE")}</span>
                      <span className="font-mono" style={{ color: "var(--color-text)" }}>{p.price ? `$${p.price.toFixed(2)}` : "—"}</span>
                      <span style={{ color: p.in_stock ? "#10B981" : "#EF4444" }}>{p.in_stock === null ? "—" : p.in_stock ? "In stock" : "Out"}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
