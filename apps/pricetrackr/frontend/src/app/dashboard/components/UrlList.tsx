"use client";
import { Bell, BellOff, Trash2, Check, X, Loader2, Send } from "lucide-react";
import { useState } from "react";
import { TrackedUrl, AlertConfig } from "./DashboardClient";

interface UrlListProps {
  trackers: TrackedUrl[];
  selectedId: number | null;
  onSelect: (t: TrackedUrl) => void;
  onUpdateFrequency: (id: number, hours: number) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
  alertConfigs: Record<number, AlertConfig>;
  onToggleAlertPanel: (id: number) => void;
  onSaveAlert: (id: number, threshold: string) => Promise<void>;
  onTestAlert: (id: number) => Promise<void>;
  deletingIds: Set<number>;
}

export default function UrlList({
  trackers,
  selectedId,
  onSelect,
  onUpdateFrequency,
  onDelete,
  alertConfigs,
  onToggleAlertPanel,
  onSaveAlert,
  onTestAlert,
  deletingIds,
}: UrlListProps) {
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  const priceDiff = (t: TrackedUrl) => {
    if (t.current_price === null || t.previous_price === null) return null;
    const curr = parseFloat(t.current_price as any);
    const prev = parseFloat(t.previous_price as any);
    if (prev === 0) return null;
    return ((curr - prev) / prev) * 100;
  };

  const isMinHistoric = (t: TrackedUrl) => {
    if (t.current_price === null || t.min_price === null) return false;
    return parseFloat(t.current_price as any) <= parseFloat(t.min_price as any);
  };

  const handleDeleteClick = (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (deleteConfirmId === id) {
      onDelete(id);
      setDeleteConfirmId(null);
    } else {
      setDeleteConfirmId(id);
      setTimeout(() => {
        setDeleteConfirmId((curr) => (curr === id ? null : curr));
      }, 5000);
    }
  };

  if (trackers.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      {trackers.map((t) => {
        const diff = priceDiff(t);
        const isMin = isMinHistoric(t);
        const alertCfg = alertConfigs[t.id] || {
          threshold: t.alert_threshold?.toString() || "",
          open: false,
          saving: false,
          testing: false,
          saved: t.alert_threshold !== null,
        };
        const isSelected = selectedId === t.id;
        const isDeleting = deletingIds.has(t.id);

        return (
          <div
            key={t.id}
            className="rounded-lg overflow-hidden border transition-all duration-200"
            style={{
              backgroundColor: isSelected ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.01)",
              borderColor: isSelected
                ? "rgba(99, 102, 241, 0.4)"
                : isMin
                ? "rgba(16, 185, 129, 0.2)"
                : "rgba(255, 255, 255, 0.05)",
            }}
          >
            {/* Primary card details */}
            <div
              onClick={() => onSelect(t)}
              className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer hover:bg-white/[0.02] transition-colors"
            >
              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold text-white truncate max-w-[280px]">
                    {t.label}
                  </h3>
                  {isMin && (
                    <span className="text-[9px] font-extrabold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase tracking-wide">
                      New Low
                    </span>
                  )}
                  {t.in_stock === false && (
                    <span className="text-[9px] font-extrabold px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 uppercase tracking-wide">
                      Out of Stock
                    </span>
                  )}
                  {t.status === "flagged" && (
                    <span className="text-[9px] font-extrabold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase tracking-wide">
                      Flagged Change
                    </span>
                  )}
                  {t.alert_threshold !== null && (
                    <span className="text-[9px] font-extrabold px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 uppercase tracking-wide flex items-center gap-0.5">
                      <Bell className="w-2.5 h-2.5" />
                      <span>Alert (${t.alert_threshold})</span>
                    </span>
                  )}
                </div>
                <p className="text-xs text-zinc-500 truncate max-w-[450px]">
                  {t.url}
                </p>
              </div>

              <div className="flex flex-wrap items-center justify-end gap-3" onClick={(e) => e.stopPropagation()}>
                {/* Price Display */}
                <div className="text-left md:text-right min-w-[100px]">
                  {t.current_price !== null ? (
                    <p className="text-sm font-bold font-mono text-white">
                      ${parseFloat(t.current_price as any).toFixed(2)}
                    </p>
                  ) : (
                    <p className="text-xs text-zinc-500 font-medium">Fetching price...</p>
                  )}
                  {diff !== null && (
                    <p
                      className={`text-[10px] font-bold font-mono ${
                        diff < 0 ? "text-emerald-400" : "text-red-400"
                      }`}
                    >
                      {diff < 0 ? "▼" : "▲"} {Math.abs(diff).toFixed(1)}%
                    </p>
                  )}
                </div>

                {/* Interval select dropdown */}
                <div className="flex flex-col">
                  <select
                    value={t.check_frequency_hours}
                    onChange={(e) => onUpdateFrequency(t.id, parseInt(e.target.value))}
                    className="text-xs bg-zinc-900 border border-white/5 rounded px-2 py-1 cursor-pointer font-medium text-zinc-400 focus:outline-none focus:border-indigo-500"
                  >
                    <option value={1}>1h Interval</option>
                    <option value={6}>6h Interval</option>
                    <option value={12}>12h Interval</option>
                    <option value={24}>24h Interval</option>
                  </select>
                </div>

                {/* Alert button Toggle */}
                <button
                  onClick={() => onToggleAlertPanel(t.id)}
                  className={`p-1.5 rounded-lg border transition-colors ${
                    alertCfg.open
                      ? "bg-indigo-500/10 border-indigo-500/30 text-indigo-400"
                      : "bg-zinc-900 border-white/5 text-zinc-400 hover:text-white"
                  }`}
                  title="Configure alert threshold"
                >
                  {t.alert_threshold !== null ? (
                    <Bell className="w-3.5 h-3.5" />
                  ) : (
                    <BellOff className="w-3.5 h-3.5" />
                  )}
                </button>

                {/* Stop watching/Delete button */}
                <button
                  disabled={isDeleting}
                  onClick={(e) => handleDeleteClick(e, t.id)}
                  className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                    deleteConfirmId === t.id
                      ? "bg-red-500/10 border-red-500/30 text-red-400"
                      : "bg-zinc-900 border-white/5 text-zinc-400 hover:text-red-400"
                  }`}
                >
                  {isDeleting ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Trash2 className="w-3 h-3" />
                  )}
                  <span>{isDeleting ? "Removing..." : deleteConfirmId === t.id ? "Confirm Delete?" : "Delete"}</span>
                </button>
              </div>
            </div>

            {/* Alert config panel inside the card */}
            {alertCfg.open && (
              <div className="px-4 pb-4 border-t border-white/5 pt-3 bg-zinc-950/20 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="space-y-0.5">
                    <p className="text-xs font-semibold text-white">Price Alert Threshold</p>
                    <p className="text-[10px] text-zinc-500">
                      Receive an instant email when the price drops below this value.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="relative">
                      <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs font-mono text-zinc-500">
                        $
                      </span>
                      <input
                        type="number"
                        step="0.01"
                        placeholder={t.current_price ? (parseFloat(t.current_price as any) * 0.9).toFixed(2) : "0.00"}
                        value={alertCfg.threshold}
                        onChange={(e) => {
                          const val = e.target.value;
                          onToggleAlertPanel(t.id); // Triggers state update
                          // We pass the new value by executing onSaveAlert/onToggleAlertPanel state logic in DashboardClient
                        }}
                        className="input-field pl-5 py-1 text-xs w-28 font-mono"
                        id={`alert-threshold-input-${t.id}`}
                      />
                    </div>
                    <button
                      onClick={() => {
                        const inputEl = document.getElementById(`alert-threshold-input-${t.id}`) as HTMLInputElement;
                        onSaveAlert(t.id, inputEl?.value || "");
                      }}
                      disabled={alertCfg.saving}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white transition-colors"
                    >
                      {alertCfg.saving ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Check className="w-3.5 h-3.5" />
                      )}
                      <span>Save</span>
                    </button>
                    <button
                      onClick={() => onTestAlert(t.id)}
                      disabled={alertCfg.testing}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-zinc-900 border border-white/5 text-zinc-300 hover:bg-zinc-800 transition-colors"
                    >
                      {alertCfg.testing ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Send className="w-3 h-3" />
                      )}
                      <span>Test Alert</span>
                    </button>
                    <button
                      onClick={() => onToggleAlertPanel(t.id)}
                      className="p-1 rounded bg-zinc-900 border border-white/5 text-zinc-400 hover:text-white"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
