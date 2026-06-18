"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { apiClient, downloadFile, trackEvent, uploadFile } from "@devforge/core";
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
  Sparkles, MessageSquare, Download, Upload, ChevronDown,
  Copy, Check, X, FileText, AlertCircle, Loader2
} from "lucide-react";

interface FeedbackEntry {
  id: number;
  text: string;
  sentiment: "positive" | "negative" | "neutral" | null;
  confidence: number | null;
  themes: string[] | null;
  is_urgent: boolean | null;
  draft_reply: string | null;
  analyzed_at: string | null;
  created_at: string;
  status: string;
}

const sentimentConfig = {
  positive: { label: "Positive", color: "#10B981", bg: "rgba(16,185,129,0.12)" },
  negative: { label: "Negative", color: "#EF4444", bg: "rgba(239,68,68,0.12)" },
  neutral:  { label: "Neutral",  color: "#A3A3A3", bg: "rgba(163,163,163,0.12)" },
};

type Tab = "single" | "bulk";
type ExportFormat = "csv" | "xlsx" | "json";

interface WeeklySummary {
  summary_text: string;
  total: number;
  urgent_count: number;
  sentiment_stats: Record<"positive" | "negative" | "neutral", number>;
  top_themes: string[];
  trend: {
    previous_total: number;
    total_delta: number;
    previous_negative: number;
    negative_delta: number;
    previous_urgent: number;
    urgent_delta: number;
  };
}

export default function DashboardPage() {
  const [entries, setEntries]         = useState<FeedbackEntry[]>([]);
  const [text, setText]               = useState("");
  const [analyzing, setAnalyzing]     = useState<Set<number>>(new Set());
  const [draftingIds, setDraftingIds] = useState<Set<number>>(new Set());
  const [selected, setSelected]       = useState<FeedbackEntry | null>(null);
  const [submitting, setSubmitting]   = useState(false);
  const [filter, setFilter]           = useState<"all" | "urgent" | "negative">("all");
  const [tab, setTab]                 = useState<Tab>("single");
  const [bulkText, setBulkText]       = useState("");
  const [bulkImporting, setBulkImporting] = useState(false);
  const [bulkResult, setBulkResult]   = useState<{created: number} | null>(null);
  const [exportOpen, setExportOpen]   = useState(false);
  const [copiedReply, setCopiedReply] = useState<number | null>(null);
  const [weeklySummary, setWeeklySummary] = useState<WeeklySummary | null>(null);
  const [loading, setLoading]         = useState(true);
  const [loadError, setLoadError]     = useState(false);
  const [toast, setToast]             = useState<DashboardToast | null>(null);
  const exportRef = useRef<HTMLDivElement>(null);

  const showToast = useCallback((nextToast: DashboardToast) => {
    setToast(nextToast);
    window.setTimeout(() => setToast(null), 4500);
  }, []);

  const refreshFeedback = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    const [entriesResult, summaryResult] = await Promise.allSettled([
      apiClient.get<FeedbackEntry[]>("/feedback/list"),
      apiClient.get<WeeklySummary>("/feedback/summary/weekly"),
    ]);
    if (entriesResult.status === "fulfilled") setEntries(entriesResult.value.data);
    if (summaryResult.status === "fulfilled") setWeeklySummary(summaryResult.value.data);
    if (entriesResult.status === "rejected" && summaryResult.status === "rejected") setLoadError(true);
    setLoading(false);
  }, []);

  useEffect(() => {
    refreshFeedback();
  }, [refreshFeedback]);

  // Close export dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) setExportOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    setSubmitting(true);
    trackEvent("feature_used", { feature_name: "add_feedback" });
    try {
      const { data } = await apiClient.post<FeedbackEntry>("/feedback", { text });
      setEntries(prev => [data, ...prev]);
      setText("");
      showToast({ tone: "success", message: "Feedback saved. We are finding what your user is saying." });
      handleAnalyze(data.id);
    } catch {
      showToast({ tone: "error", message: "We could not save that feedback. Check the text and try again." });
    }
    finally { setSubmitting(false); }
  };

  const handleAnalyze = async (id: number) => {
    setAnalyzing(prev => new Set(prev).add(id));
    trackEvent("feature_used", { feature_name: "analyze_feedback" });
    try {
      const { data } = await apiClient.post<FeedbackEntry>(`/feedback/${id}/analyze`);
      setEntries(prev => prev.map(e => e.id === id ? data : e));
      if (selected?.id === id) setSelected(data);
      showToast({ tone: "success", message: "Feedback reviewed. Themes and urgency are updated." });
    } catch {
      showToast({ tone: "error", message: "We could not review this feedback. Retry from the row." });
    }
    finally { setAnalyzing(prev => { const s = new Set(prev); s.delete(id); return s; }); }
  };

  // Draft Reply Generator — Skill: gemini-api-dev
  const handleDraftReply = async (id: number) => {
    setDraftingIds(prev => new Set(prev).add(id));
    trackEvent("feature_used", { feature_name: "draft_reply" });
    try {
      const { data } = await apiClient.post<FeedbackEntry>(`/feedback/${id}/draft-reply`);
      setEntries(prev => prev.map(e => e.id === id ? data : e));
      if (selected?.id === id) setSelected(data);
      showToast({ tone: "success", message: "Reply draft is ready." });
    } catch {
      showToast({ tone: "error", message: "We could not write a reply draft. Retry from the feedback row." });
    }
    finally { setDraftingIds(prev => { const s = new Set(prev); s.delete(id); return s; }); }
  };

  const handleCopyReply = (id: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedReply(id);
    showToast({ tone: "success", message: "Reply draft copied." });
    setTimeout(() => setCopiedReply(null), 2000);
  };

  // Bulk Import — Skill: react-patterns
  const handleBulkImport = async () => {
    const texts = bulkText.split("\n").map(t => t.trim()).filter(Boolean);
    if (!texts.length) return;
    setBulkImporting(true);
    trackEvent("feature_used", { feature_name: "bulk_import_feedback" });
    try {
      const { data } = await apiClient.post<{created: number}>("/feedback/bulk", { texts });
      setBulkResult(data);
      setBulkText("");
      // Reload entries
      const { data: newEntries } = await apiClient.get<FeedbackEntry[]>("/feedback/list");
      setEntries(newEntries);
      showToast({ tone: "success", message: `${data.created} feedback items imported.` });
    } catch {
      showToast({ tone: "error", message: "We could not import those feedback items. Keep one item per line and try again." });
    }
    finally { setBulkImporting(false); }
  };

  const handleBulkCsvUpload = async (file: File) => {
    setBulkImporting(true);
    trackEvent("feature_used", { feature_name: "bulk_import_csv" });
    const formData = new FormData();
    formData.append("file", file);
    try {
      const { data } = await uploadFile<{ created: number }>("/feedback/bulk-csv", formData);
      setBulkResult({ created: data.created });
      const { data: newEntries } = await apiClient.get<FeedbackEntry[]>("/feedback/list");
      setEntries(newEntries);
      showToast({ tone: "success", message: `${data.created} feedback items imported from CSV.` });
    } catch {
      showToast({ tone: "error", message: "We could not read that CSV. Check that it has a text column." });
    }
    finally { setBulkImporting(false); }
  };

  // Export — Skill: react-patterns
  const handleExport = async (format: ExportFormat) => {
    setExportOpen(false);
    trackEvent("feature_used", { feature_name: "export_feedback", format });
    try {
      await downloadFile(`/feedback/export?format=${format}`, `feedbacklens_export.${format}`);
      showToast({ tone: "success", message: `Your feedback export started as ${format.toUpperCase()}.` });
    } catch {
      showToast({ tone: "error", message: "We could not export your feedback. Retry from the export menu." });
    }
  };

  const urgent   = entries.filter(e => e.is_urgent);
  const negative = entries.filter(e => e.sentiment === "negative");
  const positive = entries.filter(e => e.sentiment === "positive");
  const filtered = entries.filter(e => {
    if (filter === "urgent")   return e.is_urgent;
    if (filter === "negative") return e.sentiment === "negative";
    return true;
  });

  return (
    <div className="flex gap-6">
      <ActionToast toast={toast} onDismiss={() => setToast(null)} />
      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "var(--color-text)" }}>What your users are saying</h1>
            <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{entries.length} feedback items reviewed</p>
          </div>
          {/* Export Dropdown */}
          <div className="relative w-full sm:w-auto" ref={exportRef}>
            <button
              onClick={() => setExportOpen(!exportOpen)}
              className="flex w-full sm:w-auto items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all"
              style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)" }}
            >
              <Download size={15} />
              <span>Export feedback</span>
              <ChevronDown size={14} className={`transition-transform ${exportOpen ? "rotate-180" : ""}`} />
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
        </div>

        {loadError && (
          <div className="mb-6">
            <InlineErrorState
              title="We could not load your feedback"
              description="Your feedback dashboard did not load. Retry now, and contact support if it keeps happening."
              onRetry={refreshFeedback}
            />
          </div>
        )}

        {loading && entries.length === 0 && <DashboardSkeleton rows={4} metrics={3} />}

        {!loading && !loadError && entries.length === 0 && (
          <WelcomeSteps
            title="Add your first user comment"
            description="See this week's trend, the most mentioned topic, and which messages need a reply."
            steps={[
              "Paste one user comment or import a CSV.",
              "Review themes, urgency, and this week's trend.",
              "Copy a reply draft when a user needs a response.",
            ]}
            actionLabel="Add first feedback"
            onAction={() => setTab("single")}
          />
        )}

        {!loading && (
        <>
        {/* Urgent alert */}
        {urgent.length > 0 && (
          <div className="p-4 rounded-lg mb-6 flex items-start gap-3"
            style={{ backgroundColor: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)" }}>
            <div className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0 animate-pulse" style={{ backgroundColor: "#EF4444" }} />
            <div>
              <p className="text-sm font-bold" style={{ color: "#EF4444" }}>
                {urgent.length} urgent message{urgent.length > 1 ? "s" : ""} from your users
              </p>
              <p className="text-xs mt-0.5" style={{ color: "var(--color-text-secondary)" }}>
                These messages may need a faster reply because users are blocked, upset, or reporting serious issues.
              </p>
            </div>
          </div>
        )}

        {weeklySummary && (
          <div className="p-4 rounded-lg mb-6" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider mb-1" style={{ color: "var(--color-text-secondary)" }}>Weekly insight</p>
                <p className="text-sm" style={{ color: "var(--color-text)" }}>{weeklySummary.summary_text}</p>
                {weeklySummary.top_themes.length > 0 && (
                  <div className="flex gap-1 mt-3 flex-wrap">
                    {weeklySummary.top_themes.map(theme => (
                      <span key={theme} className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: "var(--color-surface-high)", color: "var(--color-text-secondary)" }}>
                        {theme}
                      </span>
                    ))}
                  </div>
                )}
                <div className="grid grid-cols-3 gap-2 mt-4">
                  {[
                    { label: "Volume", value: weeklySummary.trend.total_delta },
                    { label: "Negative", value: weeklySummary.trend.negative_delta },
                    { label: "Urgent", value: weeklySummary.trend.urgent_delta },
                  ].map(item => (
                    <div key={item.label} className="px-2 py-1 rounded" style={{ backgroundColor: "var(--color-surface-high)" }}>
                      <p className="text-[10px] uppercase opacity-50">{item.label}</p>
                      <p className={`text-xs font-mono font-bold ${item.value > 0 ? "text-amber-500" : item.value < 0 ? "text-emerald-500" : "opacity-60"}`}>
                        {item.value > 0 ? "+" : ""}{item.value}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-xl font-mono font-bold text-[var(--color-accent)]">{weeklySummary.total}</p>
                <p className="text-[10px] uppercase opacity-50">this week</p>
              </div>
            </div>
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          {[
            { label: "Positive",  value: positive.length, color: "#10B981" },
            { label: "Negative",  value: negative.length, color: "#EF4444" },
            { label: "Needs reply",   value: urgent.length,   color: "#F59E0B" },
          ].map(s => (
            <div key={s.label} className="p-4 rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
              <p className="text-xs mb-1" style={{ color: "var(--color-text-secondary)" }}>{s.label}</p>
              <p className="text-xl font-bold font-mono" style={{ color: s.color }}>{s.value}</p>
            </div>
          ))}
        </div>

        {/* Input Tabs — Single vs Bulk */}
        <div className="mb-4 flex gap-2">
          {(["single", "bulk"] as Tab[]).map(t => (
            <button key={t} onClick={() => { setTab(t); setBulkResult(null); }}
              className="text-xs font-medium px-4 py-2 rounded-md transition-colors flex items-center gap-1.5"
              style={{
                backgroundColor: tab === t ? "var(--color-accent-dim)" : "var(--color-surface)",
                color: tab === t ? "var(--color-accent)" : "var(--color-text-secondary)",
              }}>
              {t === "single" ? <><MessageSquare size={12} /> One comment</> : <><Upload size={12} /> Bulk import</>}
            </button>
          ))}
        </div>

        {/* Single feedback form */}
        {tab === "single" && (
          <form onSubmit={handleSubmit} className="p-4 rounded-lg mb-6" style={{ backgroundColor: "var(--color-surface)" }}>
            <textarea value={text} onChange={e => setText(e.target.value)}
              className="input-field w-full h-24 mb-3 resize-none"
              placeholder="Paste a user comment, review, or support ticket..." />
            <button type="submit" disabled={submitting || !text.trim()} className="btn-primary w-full"
              style={{ opacity: submitting || !text.trim() ? 0.6 : 1 }}>
              {submitting ? "Saving and reviewing" : "Review feedback"}
            </button>
          </form>
        )}

        {/* Bulk Import */}
        {tab === "bulk" && (
          <div className="p-4 rounded-lg mb-6 space-y-3" style={{ backgroundColor: "var(--color-surface)" }}>
            <p className="text-xs font-medium" style={{ color: "var(--color-text-secondary)" }}>
              One feedback item per line, or upload a CSV with a <code className="bg-black/10 px-1 rounded">text</code> column.
            </p>
            <textarea value={bulkText} onChange={e => setBulkText(e.target.value)}
              className="input-field w-full h-32 resize-none font-mono text-xs"
              placeholder={"User comment 1...\nUser comment 2...\nUser comment 3..."} />
            <div className="flex items-center gap-3">
              <button onClick={handleBulkImport} disabled={bulkImporting || !bulkText.trim()}
                className="btn-primary flex-1 flex items-center justify-center gap-2"
                style={{ opacity: bulkImporting || !bulkText.trim() ? 0.6 : 1 }}>
                {bulkImporting ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                {bulkImporting ? "Importing feedback" : `Import ${bulkText.split("\n").filter(Boolean).length} items`}
              </button>
              <label className="px-4 py-2 rounded-lg text-sm font-medium cursor-pointer transition-colors flex items-center gap-2"
                style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text)" }}>
                <FileText size={14} />
                Upload CSV
                <input type="file" accept=".csv" className="hidden" onChange={e => {
                  const f = e.target.files?.[0];
                  if (f) handleBulkCsvUpload(f);
                }} />
              </label>
            </div>
            {bulkResult && (
              <div className="flex items-center gap-2 p-3 rounded-lg animate-in fade-in"
                style={{ backgroundColor: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.3)" }}>
                <Check size={14} className="text-emerald-500" />
                <p className="text-sm font-medium text-emerald-500">{bulkResult.created} feedback items imported</p>
              </div>
            )}
          </div>
        )}

        {/* Filter tabs */}
        <div className="flex gap-2 mb-4">
          {(["all", "urgent", "negative"] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className="text-xs font-medium px-4 py-2 rounded-md transition-colors"
              style={{
                backgroundColor: filter === f ? "var(--color-accent-dim)" : "var(--color-surface)",
                color: filter === f ? "var(--color-accent)" : "var(--color-text-secondary)",
              }}>
              {f === "all" ? `All (${entries.length})` : f === "urgent" ? `Needs reply (${urgent.length})` : `Negative (${negative.length})`}
            </button>
          ))}
        </div>

        {/* Entry list */}
        <div className="space-y-3">
          {filtered.length === 0 && (
            <div className="p-12 text-center rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
              <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
                {filter === "all" ? "Add your first user comment above." : "No feedback matches this filter."}
              </p>
            </div>
          )}
          {filtered.map(entry => {
            const cfg = entry.sentiment ? sentimentConfig[entry.sentiment] : null;
            const isDrafting = draftingIds.has(entry.id);
            return (
              <div key={entry.id} onClick={() => setSelected(entry)}
                className="p-4 rounded-lg cursor-pointer transition-colors"
                style={{
                  backgroundColor: selected?.id === entry.id ? "var(--color-surface-raised)" : "var(--color-surface)",
                  border: entry.is_urgent ? "1px solid rgba(239,68,68,0.4)" : "1px solid transparent",
                }}>
                <div className="flex items-start justify-between gap-4">
                  <p className="text-sm line-clamp-2" style={{ color: "var(--color-text)" }}>{entry.text}</p>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {entry.is_urgent && (
                      <span className="text-xs font-bold px-2 py-0.5 rounded-full"
                        style={{ backgroundColor: "rgba(239,68,68,0.15)", color: "#EF4444" }}>NEEDS REPLY</span>
                    )}
                    {cfg && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full"
                        style={{ backgroundColor: cfg.bg, color: cfg.color }}>{cfg.label}</span>
                    )}
                    {/* Draft Reply button — Skill: gemini-api-dev */}
                    {entry.analyzed_at && !entry.draft_reply && (
                      <button onClick={e => { e.stopPropagation(); handleDraftReply(entry.id); }}
                        disabled={isDrafting}
                        className="text-xs px-2 py-1 rounded flex items-center gap-1 transition-colors"
                        style={{ backgroundColor: "rgba(99,102,241,0.1)", color: "#6366F1" }}>
                        {isDrafting ? <Loader2 size={10} className="animate-spin" /> : <Sparkles size={10} />}
                        {isDrafting ? "Writing" : "Draft reply"}
                      </button>
                    )}
                    {!entry.analyzed_at && (
                      <button onClick={e => { e.stopPropagation(); handleAnalyze(entry.id); }}
                        disabled={analyzing.has(entry.id)}
                        className="text-xs px-2 py-1 rounded"
                        style={{ backgroundColor: "var(--color-surface-high)", color: "var(--color-text-secondary)" }}>
                        {analyzing.has(entry.id) ? "Reviewing" : "Review"}
                      </button>
                    )}
                  </div>
                </div>
                {entry.themes && entry.themes.length > 0 && (
                  <div className="flex gap-1 mt-2 flex-wrap">
                    {entry.themes.map(t => (
                      <span key={t} className="text-xs px-2 py-0.5 rounded"
                        style={{ backgroundColor: "var(--color-surface-high)", color: "var(--color-text-secondary)" }}>{t}</span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        </>
        )}
      </div>

      {/* Detail panel */}
      {selected && (
        <div className="w-80 flex-shrink-0 rounded-lg p-4 space-y-4" style={{ backgroundColor: "var(--color-surface)" }}>
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>User comment</p>
            <button onClick={() => setSelected(null)} className="text-xs" style={{ color: "var(--color-text-secondary)" }}>Close</button>
          </div>
          <div className="p-3 rounded-lg" style={{ backgroundColor: "var(--color-bg)" }}>
            <p className="text-xs" style={{ color: "var(--color-text)" }}>{selected.text}</p>
          </div>
          {selected.sentiment && (() => {
            const cfg = sentimentConfig[selected.sentiment];
            return (
              <div className="grid grid-cols-2 gap-2">
                <div className="p-3 rounded-lg" style={{ backgroundColor: cfg.bg }}>
                  <p className="text-xs mb-0.5" style={{ color: "var(--color-text-secondary)" }}>How it sounds</p>
                  <p className="text-sm font-bold" style={{ color: cfg.color }}>{cfg.label}</p>
                </div>
                <div className="p-3 rounded-lg" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                  <p className="text-xs mb-0.5" style={{ color: "var(--color-text-secondary)" }}>Confidence</p>
                  <p className="text-sm font-bold font-mono" style={{ color: "var(--color-text)" }}>
                    {selected.confidence ? `${Math.round(selected.confidence * 100)}%` : "—"}
                  </p>
                </div>
              </div>
            );
          })()}

          {/* Draft Reply section */}
          {selected.draft_reply ? (
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--color-text-secondary)" }}>
                  Reply draft
                </p>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400">AI</span>
              </div>
              <div className="p-3 rounded-lg text-xs" style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text)" }}>
                {selected.draft_reply}
              </div>
              <button onClick={() => handleCopyReply(selected.id, selected.draft_reply!)}
                className="btn-secondary w-full mt-2 text-xs flex items-center justify-center gap-1.5">
                {copiedReply === selected.id ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                {copiedReply === selected.id ? "Copied" : "Copy reply draft"}
              </button>
              <button onClick={() => handleDraftReply(selected.id)} disabled={draftingIds.has(selected.id)}
                className="w-full mt-1 text-xs py-1.5 rounded-lg transition-colors flex items-center justify-center gap-1.5"
                style={{ color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>
                {draftingIds.has(selected.id) ? <Loader2 size={10} className="animate-spin" /> : <Sparkles size={10} />}
                Rewrite draft
              </button>
            </div>
          ) : selected.analyzed_at ? (
            <button onClick={() => handleDraftReply(selected.id)} disabled={draftingIds.has(selected.id)}
              className="btn-primary w-full text-xs flex items-center justify-center gap-2"
              style={{ opacity: draftingIds.has(selected.id) ? 0.6 : 1 }}>
              {draftingIds.has(selected.id) ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              {draftingIds.has(selected.id) ? "Writing reply" : "Write reply draft"}
            </button>
          ) : (
            <button onClick={() => handleAnalyze(selected.id)} disabled={analyzing.has(selected.id)}
              className="btn-primary w-full text-xs"
              style={{ opacity: analyzing.has(selected.id) ? 0.6 : 1 }}>
              {analyzing.has(selected.id) ? "Reviewing" : "Review feedback"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
