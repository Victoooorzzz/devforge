"use client";
import { useState, useCallback, useEffect, useRef } from "react";
import { apiClient, getProduct, trackEvent } from "@devforge/core";
import { ActionToast, DashboardPlanPanel } from "@devforge/ui";
import { Bell, HelpCircle, LayoutDashboard, Plus, Settings, Sparkles, TrendingDown, Package, ShieldAlert } from "lucide-react";
import UrlList from "./UrlList";
import AddUrlForm from "./AddUrlForm";
import ExportButton from "./ExportButton";
import FlaggedReview from "./FlaggedReview";
import PriceChart from "./PriceChart";

const dashboardProduct = getProduct("pricetrackr");

export interface TrackedUrl {
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
  alert_threshold: number | null;
  pending_price: number | null;
  pending_stock: boolean | null;
  pending_text: string | null;
  last_text: string | null;
}

export interface TrackerSummary {
  total_trackers: number;
  active_trackers: number;
  price_drop_count: number;
  out_of_stock_count: number;
  potential_savings: number;
}

export interface TrackerHealth {
  id: number;
  label: string;
  health: "healthy" | "stale" | "never_checked" | "price_missing" | "out_of_stock";
  severity: "ok" | "warning" | "critical";
  detail: string;
  last_checked: string | null;
  check_frequency_hours: number;
}

export interface AlertConfig {
  threshold: string;
  open: boolean;
  saving: boolean;
  testing: boolean;
  saved: boolean;
}

interface DashboardClientProps {
  initialTrackers: TrackedUrl[];
  initialSummary: TrackerSummary;
  initialHealth: TrackerHealth[];
  userEmail: string;
}

export default function DashboardClient({
  initialTrackers,
  initialSummary,
  initialHealth,
  userEmail,
}: DashboardClientProps) {
  const [trackers, setTrackers] = useState<TrackedUrl[]>(initialTrackers);
  const [summary, setSummary] = useState<TrackerSummary>(initialSummary);
  const [health, setHealth] = useState<TrackerHealth[]>(initialHealth);
  const [showAddForm, setShowAddForm] = useState(false);
  const [selected, setSelected] = useState<TrackedUrl | null>(null);
  const [deletingIds, setDeletingIds] = useState<Set<number>>(new Set());
  const [alertConfigs, setAlertConfigs] = useState<Record<number, AlertConfig>>({});
  const [toast, setToast] = useState<{ tone: "success" | "error" | "info"; message: string } | null>(null);

  const showToast = useCallback((nextToast: { tone: "success" | "error" | "info"; message: string }) => {
    setToast(nextToast);
    window.setTimeout(() => setToast(null), 4500);
  }, []);

  const refreshData = useCallback(async () => {
    try {
      const res = await fetch("/api/urls?summary=true&health=true");
      if (!res.ok) throw new Error("Failed to refresh");
      const data = await res.json();
      if (data.trackers) setTrackers(data.trackers);
      if (data.summary) setSummary(data.summary);
      if (data.health) setHealth(data.health);
    } catch (err) {
      showToast({ tone: "error", message: "Failed to reload dashboard stats." });
    }
  }, [showToast]);

  const handleAddSuccess = (newTracker: TrackedUrl) => {
    setShowAddForm(false);
    refreshData();
    trackEvent("feature_used", { feature_name: "add_tracker" });
  };

  const handleUpdateFrequency = async (id: number, hours: number) => {
    try {
      await apiClient.patch(`/trackers/${id}/frequency`, { hours });
      setTrackers((prev) =>
        prev.map((t) => (t.id === id ? { ...t, check_frequency_hours: hours } : t))
      );
      showToast({ tone: "success", message: `Tracker check interval updated to ${hours} hours.` });
      await refreshData();
    } catch (err) {
      showToast({ tone: "error", message: "Could not update interval on backend worker." });
    }
  };

  const handleDelete = async (id: number) => {
    setDeletingIds((prev) => new Set(prev).add(id));
    try {
      await apiClient.delete(`/trackers/${id}`);
      setTrackers((prev) => prev.filter((t) => t.id !== id));
      if (selected?.id === id) setSelected(null);
      showToast({ tone: "success", message: "Product is no longer being watched." });
      await refreshData();
    } catch (err) {
      showToast({ tone: "error", message: "Failed to delete monitored product." });
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  const handleToggleAlertPanel = (id: number) => {
    setAlertConfigs((prev) => {
      const current = prev[id] || {
        threshold: "",
        open: false,
        saving: false,
        testing: false,
        saved: false,
      };

      const nextThreshold = current.threshold || trackers.find((t) => t.id === id)?.alert_threshold?.toString() || "";

      return {
        ...prev,
        [id]: {
          ...current,
          threshold: nextThreshold,
          open: !current.open,
        },
      };
    });
  };

  const handleSaveAlert = async (id: number, thresholdStr: string) => {
    if (!thresholdStr) return;

    setAlertConfigs((prev) => ({
      ...prev,
      [id]: { ...prev[id], saving: true },
    }));

    try {
      await apiClient.patch(`/trackers/${id}/alert-threshold`, {
        alert_threshold: parseFloat(thresholdStr),
        alert_email: userEmail,
      });

      setAlertConfigs((prev) => ({
        ...prev,
        [id]: { ...prev[id], saving: false, open: false, saved: true },
      }));

      showToast({ tone: "success", message: "Price threshold saved successfully." });
      await refreshData();
    } catch (err) {
      setAlertConfigs((prev) => ({
        ...prev,
        [id]: { ...prev[id], saving: false },
      }));
      showToast({ tone: "error", message: "Failed to save alert threshold." });
    }
  };

  const handleTestAlert = async (id: number) => {
    setAlertConfigs((prev) => ({
      ...prev,
      [id]: { ...prev[id], testing: true },
    }));

    try {
      await apiClient.post(`/trackers/${id}/test-alert`, {});
      showToast({ tone: "success", message: "Test alert dispatched to your inbox." });
    } catch (err) {
      showToast({ tone: "error", message: "Failed to dispatch test alert email." });
    } finally {
      setAlertConfigs((prev) => ({
        ...prev,
        [id]: { ...prev[id], testing: false },
      }));
    }
  };

  // Split trackers into active (or flagged) lists
  const activeTrackers = trackers.filter((t) => t.status !== "deleted");
  const flaggedTrackers = trackers.filter((t) => t.status === "flagged");

  return (
    <div className="dashboard-motion space-y-6">
      {toast && <ActionToast toast={toast} onDismiss={() => setToast(null)} />}

      {/* Flagged review area */}
      <FlaggedReview
        flaggedTrackers={flaggedTrackers}
        onActionComplete={refreshData}
        showToast={showToast}
      />

      <DashboardPlanPanel
        product={dashboardProduct}
        quotas={[
          { label: "Active trackers", used: activeTrackers.length, limit: 5, caption: "Free active tracker quota." },
          { label: "Watched links", used: summary.total_trackers, limit: 5, caption: "Pro supports 100; Team supports 500." },
          { label: "Check frequency", used: 0, limit: 24, unit: " h", mode: "capacity", caption: "Free checks daily; Pro checks hourly; Team can check every 10 minutes." },
        ]}
      />

      <div className="flex flex-col lg:flex-row gap-6">
        <div className="flex-1 min-w-0 space-y-6">
          {/* Dashboard Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="space-y-0.5">
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                <LayoutDashboard className="w-5 h-5 text-indigo-400" />
                <span>Monitoring Hub</span>
              </h1>
              <p className="text-xs text-zinc-400">
                You are currently tracking {activeTrackers.length} product links.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <ExportButton showToast={showToast} />
              <button
                onClick={() => setShowAddForm(!showAddForm)}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 text-white transition-colors shadow-lg shadow-indigo-600/10"
              >
                <Plus className="w-4 h-4" />
                <span>Track Product</span>
              </button>
            </div>
          </div>

          {/* Add form */}
          {showAddForm && (
            <AddUrlForm
              onSuccess={handleAddSuccess}
              onCancel={() => setShowAddForm(false)}
              showToast={showToast}
            />
          )}

          {/* Stats Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              {
                label: "Watched Links",
                value: summary.total_trackers,
                color: "text-indigo-400",
                bg: "bg-indigo-500/5 border-indigo-500/10",
                icon: <Package className="w-4 h-4 text-indigo-400" />,
              },
              {
                label: "Price Drops",
                value: summary.price_drop_count,
                color: "text-emerald-400",
                bg: "bg-emerald-500/5 border-emerald-500/10",
                icon: <TrendingDown className="w-4 h-4 text-emerald-400" />,
              },
              {
                label: "Out of Stock",
                value: summary.out_of_stock_count,
                color: summary.out_of_stock_count > 0 ? "text-red-400" : "text-zinc-500",
                bg: summary.out_of_stock_count > 0 ? "bg-red-500/5 border-red-500/10" : "bg-zinc-500/5 border-white/5",
                icon: <ShieldAlert className="w-4 h-4" />,
              },
              {
                label: "Potential Savings",
                value: `$${summary.potential_savings.toFixed(2)}`,
                color: "text-amber-400",
                bg: "bg-amber-500/5 border-amber-500/10",
                icon: <Sparkles className="w-4 h-4 text-amber-400" />,
              },
            ].map((stat, idx) => (
              <div
                key={idx}
                className={`dashboard-card-motion p-4 rounded-xl border flex flex-col justify-between h-24 backdrop-blur-md ${stat.bg}`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                    {stat.label}
                  </span>
                  {stat.icon}
                </div>
                <span className={`text-xl font-bold font-mono tracking-tight ${stat.color}`}>
                  {stat.value}
                </span>
              </div>
            ))}
          </div>

          <div className="dashboard-card-motion rounded-xl border border-emerald-500/10 bg-emerald-500/5 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="space-y-1">
                <span className="inline-flex w-fit items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-emerald-300">
                  <TrendingDown className="h-3 w-3" />
                  Price drop detected
                </span>
                <p className="text-sm font-semibold text-white">Webhook alert preview</p>
                <p className="text-xs text-zinc-400">
                  When a monitored price falls below your threshold, PriceTrackr can send the product, old price, new price, and link to email, Slack, or Discord.
                </p>
              </div>
              <div className="rounded-lg border border-white/5 bg-zinc-950/60 px-3 py-2 font-mono text-[10px] text-emerald-200">
                {"{ \"event\": \"price_drop\", \"source\": \"Shopify JSON-LD\", \"new_price\": 79.00 }"}
              </div>
            </div>
          </div>

          {/* Health Alerts Panel */}
          {health.some((h) => h.severity !== "ok") && (
            <div className="dashboard-card-motion bg-zinc-950/40 border border-white/5 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-white/5 pb-2">
                <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                  Price Scrape Health Status
                </span>
                <span className="text-[10px] font-mono text-zinc-500">
                  {health.filter((h) => h.severity !== "ok").length} Scrape issues
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {health
                  .filter((h) => h.severity !== "ok")
                  .slice(0, 4)
                  .map((item) => (
                    <div
                      key={item.id}
                      className="p-3 rounded-lg bg-zinc-900/60 border border-white/5 flex items-start justify-between gap-3"
                    >
                      <div className="space-y-0.5 text-left">
                        <p className="text-xs font-bold text-white truncate max-w-[200px]">
                          {item.label}
                        </p>
                        <p className="text-[10px] text-zinc-500 leading-tight">
                          {item.detail}
                        </p>
                      </div>
                      <span
                        className={`text-[8px] font-extrabold uppercase px-1.5 py-0.5 rounded flex-shrink-0 ${
                          item.severity === "critical"
                            ? "bg-red-500/10 text-red-400 border border-red-500/20"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}
                      >
                        {item.health.replace("_", " ")}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Url List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                Products Monitored
              </span>
              <span className="text-[10px] font-mono text-zinc-500">
                {activeTrackers.length} Items total
              </span>
            </div>
            {activeTrackers.length === 0 ? (
              <div className="dashboard-card-motion text-center py-12 bg-zinc-950/20 border border-white/5 rounded-xl">
                <p className="text-sm text-zinc-500 font-medium">Add your first product</p>
                <p className="text-xs text-zinc-600 mt-1">
                  Use a scrapeable product URL from Shopify-friendly stores, Best Buy, or Newegg to start monitoring price drops.
                </p>
              </div>
            ) : (
              <UrlList
                trackers={activeTrackers}
                selectedId={selected?.id || null}
                onSelect={(t) => setSelected(t)}
                onUpdateFrequency={handleUpdateFrequency}
                onDelete={handleDelete}
                alertConfigs={alertConfigs}
                onToggleAlertPanel={handleToggleAlertPanel}
                onSaveAlert={handleSaveAlert}
                onTestAlert={handleTestAlert}
                deletingIds={deletingIds}
              />
            )}
          </div>
        </div>

        {/* Sidebar History Detail Panel */}
        {selected && (
          <div className="dashboard-card-motion w-full lg:w-80 flex-shrink-0 bg-zinc-950/20 border border-white/5 rounded-xl p-4 space-y-4 h-fit backdrop-blur-md">
            <div className="flex items-center justify-between pb-2 border-b border-white/5">
              <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider truncate max-w-[200px]">
                {selected.label}
              </span>
              <button
                onClick={() => setSelected(null)}
                className="text-[10px] text-zinc-500 hover:text-white uppercase font-bold"
              >
                Close
              </button>
            </div>

            <PriceChart trackerId={selected.id} label={selected.label} />

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2.5 rounded-lg bg-zinc-900 border border-white/5">
                <span className="text-zinc-500 block mb-0.5 text-[9px] uppercase tracking-wider">
                  Min Price Registered
                </span>
                <span className="font-mono font-bold text-emerald-400">
                  {selected.min_price !== null ? `$${parseFloat(selected.min_price as any).toFixed(2)}` : "—"}
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-zinc-900 border border-white/5">
                <span className="text-zinc-500 block mb-0.5 text-[9px] uppercase tracking-wider">
                  Last Scrape Status
                </span>
                <span
                  className={`font-semibold ${
                    selected.in_stock === false ? "text-red-400" : "text-emerald-400"
                  }`}
                >
                  {selected.in_stock === null ? "—" : selected.in_stock ? "In stock" : "Out of stock"}
                </span>
              </div>
            </div>

            {selected.last_checked && (
              <p className="text-[10px] text-zinc-500 text-center">
                Last checked: {new Date(selected.last_checked).toLocaleString()}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
