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
import { 
  Activity, Trash2, RefreshCcw, Copy, Check, Search, Code,
  Database, X, ChevronRight, Send, AlertCircle, Download, ChevronDown
} from "lucide-react";

interface WebhookRequest {
  id: number;
  method: string;
  path: string;
  headers: Record<string, string>;
  body: string;
  received_at: string;
  retry_count: number;
  last_retry_status: number | null;
  auto_retry_enabled: boolean;
}

const methodColors: Record<string, string> = {
  GET: "#10B981", POST: "#6366F1", PUT: "#F59E0B", DELETE: "#EF4444", PATCH: "#8B5CF6",
};

type ExportFormat = "csv" | "xlsx" | "json";
type LogStatusFilter = "all" | "failed" | "successful" | "pending" | "auto_retry";

interface WebhookSummary {
  total_requests: number;
  recent_24h: number;
  retry_pressure: number;
  failed_forwards: number;
  auto_retry_enabled: number;
}

export default function DashboardPage() {
  const [requests, setRequests]       = useState<WebhookRequest[]>([]);
  const [selected, setSelected]       = useState<WebhookRequest | null>(null);
  const [endpointUrl, setEndpointUrl] = useState("");
  const [search, setSearch]           = useState("");
  const [copied, setCopied]           = useState(false);
  const [retryPayload, setRetryPayload] = useState("");
  const [isEditingPayload, setIsEditingPayload] = useState(false);
  const [isRetrying, setIsRetrying]   = useState(false);
  const [exportOpen, setExportOpen]   = useState(false);
  const [summary, setSummary]         = useState<WebhookSummary | null>(null);
  const [logStatus, setLogStatus]     = useState<LogStatusFilter>("all");
  const [loading, setLoading]         = useState(true);
  const [loadError, setLoadError]     = useState(false);
  const [toast, setToast]             = useState<DashboardToast | null>(null);
  const intervalRef                   = useRef<NodeJS.Timeout | null>(null);
  const exportRef                     = useRef<HTMLDivElement>(null);

  const showToast = useCallback((nextToast: DashboardToast) => {
    setToast(nextToast);
    window.setTimeout(() => setToast(null), 4500);
  }, []);

  const refreshWebhooks = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setLoadError(false);
    const [configResult, summaryResult, logsResult] = await Promise.allSettled([
      apiClient.get<{ endpoint_url: string }>("/webhooks/config"),
      apiClient.get<WebhookSummary>("/webhooks/summary"),
      apiClient.get<WebhookRequest[]>(`/webhooks/logs?status=${logStatus}`),
    ]);

    if (configResult.status === "fulfilled") setEndpointUrl(configResult.value.data.endpoint_url);
    if (summaryResult.status === "fulfilled") setSummary(summaryResult.value.data);
    if (logsResult.status === "fulfilled") setRequests(logsResult.value.data);
    if (configResult.status === "rejected" && summaryResult.status === "rejected" && logsResult.status === "rejected") {
      setLoadError(true);
    }
    if (showLoading) setLoading(false);
  }, [logStatus]);

  useEffect(() => {
    refreshWebhooks();
    intervalRef.current = setInterval(() => refreshWebhooks(false), 5000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [refreshWebhooks]);

  // Close export dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) setExportOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    if (selected) {
      setRetryPayload(selected.body);
      setIsEditingPayload(false);
    }
  }, [selected]);

  const handleClearHistory = async () => {
    if (!window.confirm("Clear your connection history? This cannot be undone.")) return;
    trackEvent("feature_used", { feature_name: "clear_webhook_history" });
    try {
      // DELETE /webhooks/requests
      await apiClient.delete("/webhooks/requests");
      setRequests([]);
      setSelected(null);
      showToast({ tone: "success", message: "Your connection history was cleared." });
    } catch {
      showToast({ tone: "error", message: "We could not clear your history. Retry in a moment." });
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(endpointUrl);
    setCopied(true);
    showToast({ tone: "success", message: "Your connection URL was copied." });
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRetry = async () => {
    if (!selected) return;
    setIsRetrying(true);
    trackEvent("feature_used", { feature_name: "retry_webhook", custom_payload: isEditingPayload });
    try {
      const payload = isEditingPayload ? retryPayload : null;
      // POST /webhooks/requests/{id}/retry
      await apiClient.post(`/webhooks/requests/${selected.id}/retry`, {
        payload_override: payload,
        schedule_auto_retry: false,
      });
      showToast({ tone: "success", message: "Retry queued. We are sending this connection again." });
    } catch (err: any) {
      showToast({ tone: "error", message: err.response?.data?.detail || "We could not retry this delivery. Check the payload and try again." });
    } finally {
      setIsRetrying(false);
    }
  };

  // Export — GET /webhooks/logs/export?format=csv|xlsx|json
  const handleExport = async (format: ExportFormat) => {
    setExportOpen(false);
    trackEvent("feature_used", { feature_name: "export_webhook_logs", format });
    try {
      await downloadFile(`/webhooks/logs/export?format=${format}`, `webhookmonitor_export.${format}`);
      showToast({ tone: "success", message: `Your connection logs export started as ${format.toUpperCase()}.` });
    } catch {
      showToast({ tone: "error", message: "We could not export your connection logs. Retry from the export menu." });
    }
  };

  const filtered = requests.filter(r => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      r.body.toLowerCase().includes(q) ||
      r.path.toLowerCase().includes(q) ||
      r.method.toLowerCase().includes(q)
    );
  });

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  return (
    <div className="flex flex-col h-full max-w-[1600px] mx-auto overflow-hidden">
      <ActionToast toast={toast} onDismiss={() => setToast(null)} />
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4 px-4 pt-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-1" style={{ color: "var(--color-text)" }}>Your connection</h1>
          <div className="flex items-center gap-2">
            <Activity size={14} className="text-emerald-500 animate-pulse" />
            <p className="text-xs opacity-60" style={{ color: "var(--color-text)" }}>
              Live delivery checks - {requests.length} deliveries in history
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Export Dropdown */}
          <div className="relative" ref={exportRef}>
            <button
              onClick={() => setExportOpen(!exportOpen)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all"
              style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)" }}
            >
              <Download size={14} />
              <span>Export logs</span>
              <ChevronDown size={12} className={`transition-transform ${exportOpen ? "rotate-180" : ""}`} />
            </button>
            {exportOpen && (
              <div className="absolute right-0 top-full mt-2 w-44 rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200"
                style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                {(["csv", "xlsx", "json"] as ExportFormat[]).map(f => (
                  <button key={f} onClick={() => handleExport(f)}
                    className="w-full text-left px-4 py-2.5 text-sm hover:bg-black/5 transition-colors"
                    style={{ color: "var(--color-text)" }}>
                    {f.toUpperCase()} - {f === "csv" ? "Spreadsheet" : f === "xlsx" ? "Excel" : "JSON API"}
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={handleClearHistory}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-all"
          >
            <Trash2 size={16} />
            <span>Clear history</span>
          </button>
        </div>
      </div>

      {loadError && (
        <div className="mb-6 px-4">
          <InlineErrorState
            title="We could not load your connection"
            description="Your webhook logs did not load. Retry now, and contact support if it keeps happening."
            onRetry={() => refreshWebhooks()}
          />
        </div>
      )}

      {loading && requests.length === 0 && <div className="px-4"><DashboardSkeleton rows={5} /></div>}

      {!loading && !loadError && requests.length === 0 && (
        <div className="px-4">
          <WelcomeSteps
            title="Send your first webhook"
            description="Use your connection URL to see delivered events, failed deliveries, and retries in one place."
            steps={[
              "Copy your connection URL.",
              "Send a test webhook from your app or provider.",
              "Inspect the delivery and retry it if your endpoint fails.",
            ]}
            actionLabel="Copy connection URL"
            onAction={handleCopy}
          />
        </div>
      )}

      {!loading && (
      <>
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6 px-4">
          {[
            { label: "24h volume", value: summary.recent_24h.toLocaleString(), color: "var(--color-primary)" },
            { label: "Retries", value: summary.retry_pressure.toLocaleString(), color: summary.retry_pressure ? "#F59E0B" : "#10B981" },
            { label: "Failed forwards", value: summary.failed_forwards.toLocaleString(), color: summary.failed_forwards ? "#EF4444" : "#10B981" },
            { label: "Auto retry", value: summary.auto_retry_enabled.toLocaleString(), color: "#6366F1" },
          ].map(stat => (
            <div key={stat.label} className="p-4 rounded-xl" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
              <p className="text-[10px] uppercase font-bold tracking-wider opacity-50 mb-1">{stat.label}</p>
              <p className="text-xl font-mono font-bold" style={{ color: stat.color }}>{stat.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-6 flex-1 overflow-hidden px-4 pb-4">
        {/* Main List */}
        <div className="flex-1 flex flex-col min-w-0">
          {endpointUrl && (
            <div className="p-4 rounded-xl mb-6 flex items-center justify-between gap-4 animate-in fade-in slide-in-from-top-2"
              style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
              <div className="min-w-0 flex-1">
                <p className="text-[10px] font-bold uppercase tracking-wider mb-1 opacity-50" style={{ color: "var(--color-text)" }}>
                  Your Webhook URL
                </p>
                <div className="flex items-center gap-2">
                  <Database size={14} className="text-[var(--color-primary)] shrink-0" />
                  <code className="text-sm font-mono truncate text-[var(--color-primary)]">{endpointUrl}</code>
                </div>
              </div>
              <button onClick={handleCopy} className="p-2.5 rounded-lg bg-black/5 hover:bg-black/10 transition-colors">
                {copied ? <Check size={18} className="text-emerald-500" /> : <Copy size={18} className="opacity-50" />}
              </button>
            </div>
          )}

          <div className="relative mb-4 group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 opacity-30 group-focus-within:opacity-100 transition-opacity" size={18} />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="input-field pl-10"
              placeholder="Search body, path, or method..."
            />
          </div>

          <div className="flex flex-wrap gap-1 rounded-lg p-1 mb-4" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            {([
              ["all", "All"],
              ["failed", "Failed"],
              ["successful", "2xx"],
              ["pending", "Pending"],
              ["auto_retry", "Auto retry"],
            ] as [LogStatusFilter, string][]).map(([value, label]) => (
              <button key={value} onClick={() => setLogStatus(value)}
                className="text-xs font-medium px-3 py-2 rounded-md transition-colors"
                style={{
                  backgroundColor: logStatus === value ? "var(--color-accent-dim)" : "transparent",
                  color: logStatus === value ? "var(--color-accent)" : "var(--color-text-secondary)",
                }}>
                {label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-auto rounded-xl scrollbar-hide"
            style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            {filtered.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center opacity-20 py-20">
                <Activity size={48} className="mb-4" />
                <p className="text-sm font-medium">
                  {search ? "No deliveries match your search" : "Waiting for your first webhook..."}
                </p>
              </div>
            ) : (
              <table className="w-full border-collapse">
                <thead className="sticky top-0 bg-[var(--color-surface)] z-10">
                  <tr className="border-b border-[var(--color-border)]">
                    {["Delivered", "Method", "Path", "Retries", ""].map((h, i) => (
                      <th key={i} className="text-left text-[10px] font-bold uppercase tracking-widest px-4 py-4 opacity-50"
                        style={{ color: "var(--color-text)" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border)]/50">
                  {filtered.map(req => (
                    <tr key={req.id}
                      onClick={() => setSelected(req)}
                      className="group cursor-pointer transition-all hover:bg-black/5"
                      style={{
                        backgroundColor: selected?.id === req.id ? "rgba(var(--color-primary-rgb), 0.05)" : "transparent",
                      }}>
                      <td className="px-4 py-4 text-xs font-mono opacity-50">{formatTime(req.received_at)}</td>
                      <td className="px-4 py-4">
                        <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded border"
                          style={{
                            backgroundColor: `${methodColors[req.method] || "#A3A3A3"}15`,
                            color: methodColors[req.method] || "#A3A3A3",
                            borderColor: `${methodColors[req.method] || "#A3A3A3"}30`
                          }}>
                          {req.method}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-xs font-mono truncate max-w-[200px] md:max-w-md"
                        style={{ color: "var(--color-text)" }}>{req.path}</td>
                      <td className="px-4 py-4 text-xs font-mono text-center">
                        {req.retry_count > 0 ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold"
                            style={{ backgroundColor: "rgba(239,68,68,0.1)", color: "#EF4444" }}>
                            {req.retry_count}x
                          </span>
                        ) : (
                          <span className="opacity-20">—</span>
                        )}
                      </td>
                      <td className="px-4 py-4 text-right">
                        <ChevronRight size={16} className={`ml-auto transition-transform ${selected?.id === req.id ? "rotate-90 text-[var(--color-primary)]" : "opacity-0 group-hover:opacity-30"}`} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Inspector Panel */}
        {selected ? (
          <div className="w-full lg:w-[450px] flex flex-col rounded-xl overflow-hidden animate-in slide-in-from-right-4 duration-300"
            style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-black/5">
              <div className="flex items-center gap-2">
                <Code size={16} className="text-[var(--color-primary)]" />
                <h2 className="text-sm font-bold uppercase tracking-wider">Inspector</h2>
                {/* Retry status badge */}
                {selected.last_retry_status && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded"
                    style={{
                      backgroundColor: selected.last_retry_status >= 200 && selected.last_retry_status < 300 ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)",
                      color: selected.last_retry_status >= 200 && selected.last_retry_status < 300 ? "#10B981" : "#EF4444"
                    }}>
                    {selected.last_retry_status}
                  </span>
                )}
              </div>
              <button onClick={() => setSelected(null)} className="p-1.5 rounded-lg hover:bg-black/10 transition-colors">
                <X size={18} className="opacity-50" />
              </button>
            </div>

            <div className="flex-1 overflow-auto p-6 space-y-8 scrollbar-hide">
              <section>
                <h3 className="text-[10px] font-bold uppercase tracking-widest mb-3 opacity-50">Headers</h3>
                <div className="rounded-lg bg-black/20 p-4 font-mono text-[11px] leading-relaxed overflow-x-auto">
                  {Object.entries(selected.headers).map(([k, v]) => (
                    <div key={k} className="flex gap-2">
                      <span className="text-indigo-400 shrink-0">{k}:</span>
                      <span className="opacity-80 break-all">{v}</span>
                    </div>
                  ))}
                </div>
              </section>

              <section className="flex-1 flex flex-col">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-[10px] font-bold uppercase tracking-widest opacity-50">Payload</h3>
                  <button
                    onClick={() => setIsEditingPayload(!isEditingPayload)}
                    className={`text-[10px] font-bold uppercase px-2 py-1 rounded transition-colors ${isEditingPayload ? "bg-amber-500/10 text-amber-500" : "bg-black/10 hover:bg-black/20"}`}
                  >
                    {isEditingPayload ? "Cancel edit" : "Edit and retry"}
                  </button>
                </div>

                {isEditingPayload ? (
                  <div className="flex-1 flex flex-col gap-2">
                    <textarea
                      value={retryPayload}
                      onChange={e => setRetryPayload(e.target.value)}
                      className="flex-1 min-h-[300px] w-full bg-black/40 text-emerald-400 font-mono text-xs p-4 rounded-lg border border-amber-500/30 focus:border-amber-500/60 focus:outline-none resize-none"
                    />
                    <div className="flex items-center gap-2 text-[10px] text-amber-500/70 p-2">
                      <AlertCircle size={12} />
                      <span>You are about to retry this delivery with an edited payload.</span>
                    </div>
                  </div>
                ) : (
                  <pre className="p-4 rounded-lg bg-black/20 font-mono text-[11px] leading-relaxed text-emerald-400/90 overflow-auto max-h-[400px]">
                    {(() => { try { return JSON.stringify(JSON.parse(selected.body), null, 2); } catch { return selected.body; } })()}
                  </pre>
                )}
              </section>
            </div>

            <div className="p-6 bg-black/5 border-t border-[var(--color-border)]">
              <button
                onClick={handleRetry}
                disabled={isRetrying}
                className={`w-full py-3 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg ${isEditingPayload ? "bg-amber-500 hover:bg-amber-600 shadow-amber-500/20" : "bg-[var(--color-primary)] hover:opacity-90 shadow-[var(--color-primary)]/20"}`}
                style={{ color: "#000", opacity: isRetrying ? 0.7 : 1 }}
              >
                {isRetrying ? <InlineSpinner /> : <Send size={18} />}
                <span>{isEditingPayload ? "Retry with edited payload" : "Retry original delivery"}</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="hidden lg:flex w-[450px] items-center justify-center rounded-xl opacity-10 border border-dashed border-[var(--color-text)]">
            <div className="text-center">
              <Code size={64} className="mx-auto mb-4" />
              <p className="font-bold">Select a delivery to inspect</p>
            </div>
          </div>
        )}
      </div>
      </>
      )}
    </div>
  );
}
