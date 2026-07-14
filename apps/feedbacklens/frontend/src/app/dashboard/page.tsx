"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { apiClient, downloadFile, getProduct, trackEvent, uploadFile } from "@devforge/core";
import {
  ActionToast,
  DashboardPlanPanel,
  DashboardEmptyState,
  DashboardSkeleton,
  InlineErrorState,
  InlineSpinner,
  WelcomeSteps,
  type DashboardToast,
} from "@devforge/ui";
import { 
  Sparkles, MessageSquare, Download, Upload, ChevronDown,
  Copy, Check, X, FileText, AlertCircle, Loader2, Trash2, Plus
} from "lucide-react";

const dashboardProduct = getProduct("feedbacklens");
const SHOW_EXTERNAL_SOURCE_CONNECTORS = false;
const SHOW_GITHUB_ISSUE_ACTION = false;

const sourceCards = [
  { name: "GitHub", detail: "Issues and comments" },
  { name: "Email", detail: "Forwarded support threads" },
  { name: "Canny", detail: "Feature requests" },
  { name: "Reddit", detail: "Community feedback" },
  { name: "X/Twitter", detail: "Public mentions" },
];

const sampleFeedback = [
  "The export keeps timing out when I filter by customer segment.",
  "Love the weekly digest, but I need one-click reply drafts for angry customers.",
  "Pricing is fair, yet duplicate requests make our roadmap meeting noisy.",
];

const FEEDBACK_ACTION_TIMEOUT_MS = 20000;

async function runFeedbackActionWithTimeout<T>(
  actionName: string,
  action: (controller: AbortController) => Promise<T>,
): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), FEEDBACK_ACTION_TIMEOUT_MS);
  try {
    return await action(controller);
  } catch (error: any) {
    if (controller.signal.aborted || error?.name === "AbortError") {
      throw new Error(`${actionName} took too long. Please retry in a moment.`);
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

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
  deduped?: boolean;
  duplicate_of_id?: number;
  analysis_engine?: string | null;
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

interface DedupeSummary {
  total_feedback: number;
  duplicate_groups: number;
  duplicate_candidates: number;
  dedupe_rate: number;
  groups: Array<{
    canonical_id: number;
    entry_ids: number[];
    duplicate_ids: number[];
    average_similarity: number;
  }>;
}

interface FeedbackSource {
  id: number;
  source_type: string;
  display_name: string;
  status: string;
  poll_frequency_hours: number | null;
  last_polled_at?: string | null;
  forward_address?: string;
  webhook_path?: string;
  config?: Record<string, unknown>;
}

interface FeedbackCluster {
  id: string;
  label: string;
  priority: "urgent" | "high" | "medium" | "low";
  mention_count: number;
  status?: string;
  sample_quotes: Array<{ text: string; source?: string; author?: string }>;
  source_counts: Record<string, number>;
  sentiment_counts: Record<string, number>;
  top_themes: string[];
}

interface ClusterResponse {
  clusters: FeedbackCluster[];
  total: number;
  days: number;
}

interface DigestPayload {
  days: number;
  summary: {
    total_feedback: number;
    clusters_active: number;
    urgent_clusters: number;
    high_clusters: number;
    low_clusters: number;
  };
  urgent: FeedbackCluster[];
  high: FeedbackCluster[];
  low: FeedbackCluster[];
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
  const [bulkResult, setBulkResult]   = useState<{created: number; duplicates_skipped?: number; total_rows?: number} | null>(null);
  const [exportOpen, setExportOpen]   = useState(false);
  const [copiedReply, setCopiedReply] = useState<number | null>(null);
  const [weeklySummary, setWeeklySummary] = useState<WeeklySummary | null>(null);
  const [dedupeSummary, setDedupeSummary] = useState<DedupeSummary | null>(null);
  const [sources, setSources]       = useState<FeedbackSource[]>([]);
  const [clusters, setClusters]     = useState<FeedbackCluster[]>([]);
  const [digest, setDigest]         = useState<DigestPayload | null>(null);
  const [githubIssueClusterId, setGithubIssueClusterId] = useState<string | null>(null);
  const [managingSources, setManagingSources] = useState(false);
  const [sourceForm, setSourceForm] = useState({ source_type: "email", display_name: "" });
  const [savingSource, setSavingSource] = useState(false);
  const [deletingSourceId, setDeletingSourceId] = useState<number | null>(null);
  const [feedbackDeleteConfirmId, setFeedbackDeleteConfirmId] = useState<number | null>(null);
  const [deletingFeedbackIds, setDeletingFeedbackIds] = useState<Set<number>>(new Set());
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
    const [entriesResult, summaryResult, dedupeResult, sourcesResult, clustersResult, digestResult] = await Promise.allSettled([
      apiClient.get<FeedbackEntry[]>("/feedback/list"),
      apiClient.get<WeeklySummary>("/feedback/summary/weekly"),
      apiClient.get<DedupeSummary>("/feedback/dedupe/summary"),
      apiClient.get<FeedbackSource[]>("/sources"),
      apiClient.get<ClusterResponse>("/clusters?days=30"),
      apiClient.get<DigestPayload>("/feedbacklens/digest?days=7"),
    ]);
    if (entriesResult.status === "fulfilled") setEntries(entriesResult.value.data);
    if (summaryResult.status === "fulfilled") setWeeklySummary(summaryResult.value.data);
    if (dedupeResult.status === "fulfilled") setDedupeSummary(dedupeResult.value.data);
    if (sourcesResult.status === "fulfilled") setSources(sourcesResult.value.data);
    if (clustersResult.status === "fulfilled") setClusters(clustersResult.value.data.clusters);
    if (digestResult.status === "fulfilled") setDigest(digestResult.value.data);
    if (
      entriesResult.status === "rejected" &&
      summaryResult.status === "rejected" &&
      dedupeResult.status === "rejected" &&
      sourcesResult.status === "rejected" &&
      clustersResult.status === "rejected" &&
      digestResult.status === "rejected"
    ) setLoadError(true);
    setLoading(false);
  }, []);

  const refreshDerivedInsights = useCallback(async () => {
    const [summaryResult, dedupeResult, clustersResult, digestResult] = await Promise.allSettled([
      apiClient.get<WeeklySummary>("/feedback/summary/weekly"),
      apiClient.get<DedupeSummary>("/feedback/dedupe/summary"),
      apiClient.get<ClusterResponse>("/clusters?days=30"),
      apiClient.get<DigestPayload>("/feedbacklens/digest?days=7"),
    ]);
    if (summaryResult.status === "fulfilled") setWeeklySummary(summaryResult.value.data);
    if (dedupeResult.status === "fulfilled") setDedupeSummary(dedupeResult.value.data);
    if (clustersResult.status === "fulfilled") setClusters(clustersResult.value.data.clusters);
    if (digestResult.status === "fulfilled") setDigest(digestResult.value.data);
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
      const { data } = await runFeedbackActionWithTimeout("Saving and reviewing feedback", (controller) =>
        apiClient.post<FeedbackEntry>("/feedback", { text }, { signal: controller.signal })
      );
      setText("");
      if (data.deduped) {
        setEntries(prev => prev.some(entry => entry.id === data.duplicate_of_id) ? prev : [data, ...prev]);
        showToast({ tone: "success", message: "Duplicate matched existing feedback. Counts stay clean." });
        refreshFeedback();
      } else {
        setEntries(prev => [data, ...prev]);
        showToast({ tone: "success", message: "Feedback saved. We are finding what your user is saying." });
        handleAnalyze(data.id);
      }
    } catch (error: any) {
      showToast({ tone: "error", message: error.message || "We could not save that feedback. Check the text and try again." });
    }
    finally { setSubmitting(false); }
  };

  const handleAnalyze = async (id: number) => {
    setAnalyzing(prev => new Set(prev).add(id));
    trackEvent("feature_used", { feature_name: "analyze_feedback" });
    try {
      const { data } = await runFeedbackActionWithTimeout("Reviewing feedback", (controller) =>
        apiClient.post<FeedbackEntry>(`/feedback/${id}/analyze`, undefined, { signal: controller.signal })
      );
      setEntries(prev => prev.map(e => e.id === id ? data : e));
      if (selected?.id === id) setSelected(data);
      await refreshFeedback();
      showToast({ tone: "success", message: "Feedback reviewed. Themes and urgency are updated." });
    } catch (error: any) {
      showToast({ tone: "error", message: error.message || "We could not review this feedback. Retry from the row." });
    }
    finally { setAnalyzing(prev => { const s = new Set(prev); s.delete(id); return s; }); }
  };

  const handleDeleteFeedback = async (entry: FeedbackEntry) => {
    if (feedbackDeleteConfirmId !== entry.id) {
      setFeedbackDeleteConfirmId(entry.id);
      showToast({ tone: "info", message: "Click Delete again to permanently remove this feedback." });
      window.setTimeout(() => setFeedbackDeleteConfirmId(current => current === entry.id ? null : current), 5000);
      return;
    }
    setFeedbackDeleteConfirmId(null);
    setDeletingFeedbackIds(prev => new Set(prev).add(entry.id));
    try {
      await apiClient.delete(`/feedback/${entry.id}`);
      setEntries(prev => prev.filter(item => item.id !== entry.id));
      if (selected?.id === entry.id) setSelected(null);
      await refreshFeedback();
      showToast({ tone: "success", message: "Feedback permanently deleted." });
    } catch {
      showToast({ tone: "error", message: "Feedback could not be deleted." });
    } finally {
      setDeletingFeedbackIds(prev => { const next = new Set(prev); next.delete(entry.id); return next; });
    }
  };

  const handleCreateSource = async () => {
    if (!sourceForm.display_name.trim()) return;
    setSavingSource(true);
    try {
      const { data } = await apiClient.post<FeedbackSource>("/sources", sourceForm);
      setSources(prev => [data, ...prev]);
      setSourceForm(current => ({ ...current, display_name: "" }));
      showToast({ tone: "success", message: `${data.display_name} source added.` });
    } catch {
      showToast({ tone: "error", message: "Source could not be added. Check your plan limit." });
    } finally {
      setSavingSource(false);
    }
  };

  const handleDeleteSource = async (source: FeedbackSource) => {
    setDeletingSourceId(source.id);
    try {
      await apiClient.delete(`/sources/${source.id}`);
      setSources(prev => prev.filter(item => item.id !== source.id));
      showToast({ tone: "success", message: `${source.display_name} removed and quota released.` });
    } catch {
      showToast({ tone: "error", message: "Source could not be removed." });
    } finally {
      setDeletingSourceId(null);
    }
  };

  const handleDraftReply = async (id: number) => {
    setDraftingIds(prev => new Set(prev).add(id));
    trackEvent("feature_used", { feature_name: "draft_reply" });
    try {
      const { data } = await runFeedbackActionWithTimeout("Writing reply draft", (controller) =>
        apiClient.post<FeedbackEntry>(`/feedback/${id}/draft-reply`, undefined, { signal: controller.signal })
      );
      setEntries(prev => prev.map(e => e.id === id ? data : e));
      if (selected?.id === id) setSelected(data);
      showToast({ tone: "success", message: "Reply draft is ready." });
    } catch (error: any) {
      showToast({ tone: "error", message: error.message || "We could not write a reply draft. Retry from the feedback row." });
    }
    finally { setDraftingIds(prev => { const s = new Set(prev); s.delete(id); return s; }); }
  };

  const handleCopyReply = (id: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedReply(id);
    showToast({ tone: "success", message: "Reply draft copied." });
    setTimeout(() => setCopiedReply(null), 2000);
  };

  const loadSampleFeedback = () => {
    setTab("bulk");
    setBulkResult(null);
    setBulkText(sampleFeedback.join("\n"));
    showToast({ tone: "info", message: "Sample feedback loaded. Review it, then import when ready." });
    trackEvent("feature_used", { feature_name: "feedbacklens_load_sample_feedback" });
  };

  const handleCreateGitHubIssue = async (cluster: FeedbackCluster) => {
    setGithubIssueClusterId(cluster.id);
    trackEvent("feature_used", { feature_name: "feedbacklens_create_github_issue", cluster_id: cluster.id });
    try {
      const { data } = await apiClient.post<{ issue_url?: string; issue_number?: number }>(
        `/clusters/${cluster.id}/github-issue`,
        { labels: ["feedbacklens", cluster.priority] },
      );
      showToast({
        tone: "success",
        message: data.issue_number ? `GitHub issue #${data.issue_number} created.` : "GitHub issue created.",
      });
    } catch (error: any) {
      showToast({
        tone: "error",
        message: error.response?.data?.detail || "Connect GitHub in sources before creating issues.",
      });
    } finally {
      setGithubIssueClusterId(null);
    }
  };

  // Bulk Import — Skill: react-patterns
  const handleBulkImport = async () => {
    const texts = bulkText.split("\n").map(t => t.trim()).filter(Boolean);
    if (!texts.length) return;
    setBulkImporting(true);
    trackEvent("feature_used", { feature_name: "bulk_import_feedback" });
    try {
      const { data } = await apiClient.post<{created: number; duplicates_skipped: number}>("/feedback/bulk", { texts });
      setBulkResult(data);
      setBulkText("");
      // Reload entries
      const { data: newEntries } = await apiClient.get<FeedbackEntry[]>("/feedback/list");
      setEntries(newEntries);
      await refreshDerivedInsights();
      showToast({ tone: "success", message: `${data.created} feedback items imported. ${data.duplicates_skipped} duplicates skipped.` });
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
      const { data } = await uploadFile<{ created: number; duplicates_skipped: number; total_rows: number }>("/feedback/bulk-csv", formData);
      setBulkResult(data);
      const { data: newEntries } = await apiClient.get<FeedbackEntry[]>("/feedback/list");
      setEntries(newEntries);
      await refreshDerivedInsights();
      showToast({ tone: "success", message: `${data.created} feedback items imported from CSV. ${data.duplicates_skipped} duplicates skipped.` });
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
    <div className="dashboard-motion flex gap-6">
      <ActionToast toast={toast} onDismiss={() => setToast(null)} />
      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "var(--color-text)" }}>What your users are saying</h1>
            <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{entries.length} feedback items processed by the system</p>
          </div>
          {/* Export Dropdown */}
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
          <button
            type="button"
            onClick={loadSampleFeedback}
            className="flex w-full sm:w-auto items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all"
            style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)" }}
          >
            <Sparkles size={15} />
            <span>Load sample feedback</span>
          </button>
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
        </div>

        <div className="mb-6">
          <DashboardPlanPanel
            product={dashboardProduct}
            quotas={[
              { label: "Feedback this month", used: entries.length },
              { label: "Duplicate groups", used: dedupeSummary?.duplicate_groups ?? 0 },
            ]}
          />
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

        {dedupeSummary && dedupeSummary.total_feedback > 0 && (
          <div className="p-4 rounded-lg mb-6" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider mb-1" style={{ color: "var(--color-text-secondary)" }}>Data quality</p>
                <p className="text-sm" style={{ color: "var(--color-text)" }}>
                  {dedupeSummary.duplicate_groups} duplicate group{dedupeSummary.duplicate_groups === 1 ? "" : "s"} found across {dedupeSummary.total_feedback} feedback items.
                </p>
                <p className="text-xs mt-1" style={{ color: "var(--color-text-secondary)" }}>
                  Near-duplicate detection keeps repeated complaints from inflating trend counts.
                </p>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-xl font-mono font-bold text-[var(--color-accent)]">{Math.round(dedupeSummary.dedupe_rate * 100)}%</p>
                <p className="text-[10px] uppercase opacity-50">matched</p>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          {SHOW_EXTERNAL_SOURCE_CONNECTORS ? (
            <div className="p-4 rounded-lg" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="flex items-center justify-between gap-3 mb-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--color-text-secondary)" }}>Sources</p>
                <p className="text-sm" style={{ color: "var(--color-text)" }}>{sources.length} connected or staged channels</p>
              </div>
              <button type="button" onClick={() => setManagingSources(value => !value)} className="text-xs font-bold text-[var(--color-accent)]">
                {managingSources ? "Done" : "Manage"}
              </button>
            </div>
            {managingSources ? (
              <div className="mb-3 space-y-2 rounded-lg p-3" style={{ backgroundColor: "var(--color-surface-high)" }}>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-[110px_1fr_auto]">
                  <select
                    value={sourceForm.source_type}
                    onChange={event => setSourceForm(current => ({ ...current, source_type: event.target.value }))}
                    className="input-field px-2 py-1.5 text-xs"
                  >
                    <option value="email">Email</option>
                    <option value="canny">Canny</option>
                    <option value="manual">Manual</option>
                    <option value="github">GitHub</option>
                    <option value="reddit">Reddit</option>
                    <option value="twitter">X/Twitter</option>
                  </select>
                  <input
                    value={sourceForm.display_name}
                    onChange={event => setSourceForm(current => ({ ...current, display_name: event.target.value }))}
                    className="input-field px-2 py-1.5 text-xs"
                    placeholder="Source name"
                  />
                  <button type="button" onClick={handleCreateSource} disabled={savingSource || !sourceForm.display_name.trim()} className="btn-primary flex items-center justify-center gap-1 px-3 py-1.5 text-xs">
                    {savingSource ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
                    Add
                  </button>
                </div>
                <p className="text-[10px]" style={{ color: "var(--color-text-secondary)" }}>
                  Email, Canny, and Manual work immediately. OAuth sources are staged until authorization is completed.
                </p>
              </div>
            ) : null}
            <div className="space-y-2">
              {sources.length === 0 ? (
                <div className="grid grid-cols-1 gap-2">
                  {sourceCards.map(source => (
                    <div key={source.name} className="rounded-lg px-3 py-2" style={{ backgroundColor: "var(--color-surface-high)" }}>
                      <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>{source.name}</p>
                      <p className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>{source.detail}</p>
                    </div>
                  ))}
                </div>
              ) : sources.slice(0, 5).map(source => (
                <div key={source.id} className="flex items-center justify-between rounded-lg px-3 py-2" style={{ backgroundColor: "var(--color-surface-high)" }}>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold" style={{ color: "var(--color-text)" }}>{source.display_name}</p>
                    <p className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>
                      {source.source_type} · every {source.poll_frequency_hours}h
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase ${source.status === "connected" ? "text-emerald-500 bg-emerald-500/10" : "text-amber-500 bg-amber-500/10"}`}>
                      {source.status}
                    </span>
                    {managingSources ? (
                      <button type="button" onClick={() => handleDeleteSource(source)} disabled={deletingSourceId === source.id} aria-label={`Delete ${source.display_name}`} className="rounded p-1 text-red-500 hover:bg-red-500/10">
                        {deletingSourceId === source.id ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
            </div>
          ) : null}

          <div className="p-4 rounded-lg" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <p className="text-xs font-bold uppercase tracking-wider mb-1" style={{ color: "var(--color-text-secondary)" }}>Weekly digest</p>
            <p className="text-sm mb-3" style={{ color: "var(--color-text)" }}>
              {digest ? `${digest.summary.clusters_active} active clusters from ${digest.summary.total_feedback} feedback items.` : "Digest endpoint is ready once feedback arrives."}
            </p>
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: "Urgent", value: digest?.summary.urgent_clusters ?? 0, tone: "text-red-500" },
                { label: "High", value: digest?.summary.high_clusters ?? 0, tone: "text-amber-500" },
                { label: "Low", value: digest?.summary.low_clusters ?? 0, tone: "text-emerald-500" },
              ].map(item => (
                <div key={item.label} className="rounded-lg p-2 text-center" style={{ backgroundColor: "var(--color-surface-high)" }}>
                  <p className={`text-lg font-mono font-bold ${item.tone}`}>{item.value}</p>
                  <p className="text-[10px] uppercase opacity-50">{item.label}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="p-4 rounded-lg" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <p className="text-xs font-bold uppercase tracking-wider mb-1" style={{ color: "var(--color-text-secondary)" }}>Topic action queue</p>
            <p className="text-sm mb-3" style={{ color: "var(--color-text)" }}>{clusters.length} topic clusters ready for triage.</p>
            <div className="space-y-2">
              {clusters.slice(0, 3).map(cluster => (
                <div key={cluster.id} className="rounded-lg p-3" style={{ backgroundColor: "var(--color-surface-high)" }}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold" style={{ color: "var(--color-text)" }}>{cluster.label}</p>
                      <p className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>
                        {cluster.mention_count} mentions · {cluster.top_themes.slice(0, 2).join(", ") || "unlabeled"}
                      </p>
                    </div>
                    {SHOW_GITHUB_ISSUE_ACTION ? (
                      <button
                        type="button"
                        onClick={() => handleCreateGitHubIssue(cluster)}
                        disabled={githubIssueClusterId === cluster.id}
                        className="rounded-md px-2 py-1 text-[10px] font-bold text-[var(--color-accent)] transition-colors hover:bg-black/10 disabled:opacity-60"
                      >
                        {githubIssueClusterId === cluster.id ? "Creating" : "GitHub Issue"}
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}
              {clusters.length === 0 ? <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>Analyze feedback to generate clusters.</p> : null}
            </div>
          </div>
        </div>

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

        <div className="mb-6 grid gap-4 md:grid-cols-2">
          <div className="rounded-lg p-4" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <p className="text-xs font-bold uppercase tracking-wider mb-1" style={{ color: "var(--color-text-secondary)" }}>ROI micro-case</p>
            <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Product team saved 8 hours/week</p>
            <p className="mt-1 text-xs" style={{ color: "var(--color-text-secondary)" }}>
              Source cards, digest clusters, and inline reply drafts keep triage out of spreadsheets.
            </p>
          </div>
          <div className="rounded-lg p-4" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <p className="text-xs font-bold uppercase tracking-wider mb-1" style={{ color: "var(--color-text-secondary)" }}>Beta offer</p>
            <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Join beta - 50% off first 3 months</p>
            <p className="mt-1 text-xs" style={{ color: "var(--color-text-secondary)" }}>
              Good fit for teams drowning in tickets, reviews, and duplicate roadmap noise.
            </p>
          </div>
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
                <p className="text-sm font-medium text-emerald-500">
                  {bulkResult.created} feedback items imported
                  {bulkResult.duplicates_skipped ? `, ${bulkResult.duplicates_skipped} duplicates skipped` : ""}
                </p>
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
                    <button
                      type="button"
                      onClick={e => { e.stopPropagation(); void handleDeleteFeedback(entry); }}
                      disabled={deletingFeedbackIds.has(entry.id)}
                      aria-label={`Delete feedback ${entry.id}`}
                      className="text-xs px-2 py-1 rounded flex items-center gap-1 text-red-500 transition-colors hover:bg-red-500/10 disabled:opacity-60"
                    >
                      {deletingFeedbackIds.has(entry.id) ? <Loader2 size={10} className="animate-spin" /> : <Trash2 size={10} />}
                      {feedbackDeleteConfirmId === entry.id ? "Confirm delete" : "Delete"}
                    </button>
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
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-500">Local</span>
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
