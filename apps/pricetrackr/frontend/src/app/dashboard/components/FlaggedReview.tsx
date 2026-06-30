"use client";
import { useState } from "react";
import { apiClient } from "@devforge/core";
import { AlertTriangle, Check, X, Loader2 } from "lucide-react";
import TextDiff from "./TextDiff";
import { TrackedUrl } from "./DashboardClient";

interface FlaggedReviewProps {
  flaggedTrackers: TrackedUrl[];
  onActionComplete: () => Promise<void>;
  showToast: (toast: { tone: "success" | "error" | "info"; message: string }) => void;
}

export default function FlaggedReview({
  flaggedTrackers,
  onActionComplete,
  showToast,
}: FlaggedReviewProps) {
  const [actingOn, setActingOn] = useState<Record<number, "confirm" | "dismiss" | null>>({});

  const handleAction = async (id: number, action: "confirm" | "dismiss") => {
    setActingOn((prev) => ({ ...prev, [id]: action }));
    try {
      await apiClient.post(`/trackers/${id}/confirm`, { action });
      showToast({
        tone: "success",
        message: `Change successfully ${action === "confirm" ? "confirmed" : "dismissed"}.`,
      });
      await onActionComplete();
    } catch (err) {
      showToast({
        tone: "error",
        message: `Failed to ${action} the price change. Please try again.`,
      });
    } finally {
      setActingOn((prev) => ({ ...prev, [id]: null }));
    }
  };

  if (flaggedTrackers.length === 0) return null;

  return (
    <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 mb-6 space-y-4">
      <div className="flex items-start gap-3">
        <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div className="space-y-0.5">
          <h3 className="text-sm font-semibold text-white">
            Manual Review Required ({flaggedTrackers.length})
          </h3>
          <p className="text-xs text-zinc-400">
            The following products had price changes greater than 50%. We flagged them to prevent false alerts.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {flaggedTrackers.map((t) => {
          const isProcessing = actingOn[t.id] !== null && actingOn[t.id] !== undefined;
          return (
            <div
              key={t.id}
              className="bg-zinc-950/40 border border-white/5 rounded-xl p-4 space-y-4"
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div>
                  <h4 className="text-sm font-semibold text-white truncate max-w-[280px]">
                    {t.label}
                  </h4>
                  <a
                    href={t.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-zinc-500 hover:text-indigo-400 truncate max-w-[280px] block"
                  >
                    {t.url}
                  </a>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-[10px] text-zinc-500 uppercase font-semibold">
                      Current Price
                    </p>
                    <p className="text-sm font-bold text-zinc-400 font-mono">
                      {t.current_price !== null ? `$${t.current_price.toFixed(2)}` : "N/A"}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-amber-400 uppercase font-semibold">
                      Pending Price
                    </p>
                    <p className="text-sm font-bold text-amber-400 font-mono">
                      {t.pending_price !== null ? `$${t.pending_price.toFixed(2)}` : "N/A"}
                    </p>
                  </div>
                </div>
              </div>

              {(t.last_text || t.pending_text) && (
                <div className="border-t border-white/5 pt-3">
                  <p className="text-[10px] text-zinc-500 uppercase font-semibold mb-2">
                    Scraped Text Content Comparison
                  </p>
                  <TextDiff oldText={t.last_text} newText={t.pending_text} />
                </div>
              )}

              <div className="flex items-center justify-end gap-2 border-t border-white/5 pt-3">
                <button
                  disabled={isProcessing}
                  onClick={() => handleAction(t.id, "dismiss")}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-zinc-900 border border-white/5 text-zinc-300 hover:bg-zinc-800 transition-colors"
                >
                  {actingOn[t.id] === "dismiss" ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <X className="w-3.5 h-3.5 text-red-400" />
                  )}
                  <span>Dismiss Change</span>
                </button>
                <button
                  disabled={isProcessing}
                  onClick={() => handleAction(t.id, "confirm")}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-700 transition-colors"
                >
                  {actingOn[t.id] === "confirm" ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Check className="w-3.5 h-3.5 text-white" />
                  )}
                  <span>Confirm & Apply</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
