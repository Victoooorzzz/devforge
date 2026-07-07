"use client";
import { useState, useCallback, useEffect, useRef } from "react";
import { trackEvent, apiClient, downloadFile, getApiUrl, getProduct, uploadAndDownloadFile, uploadFile } from "@devforge/core";
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
  FileText, Download, Trash2, CheckCircle, Clock, AlertCircle, Info,
  ChevronDown, ChevronUp, Sparkles, RefreshCw, TrendingDown, Zap, Brain, X, Copy, Check, Image as ImageIcon,
} from "lucide-react";

const dashboardProduct = getProduct("filecleaner");

interface FileReport {
  rows_original: number;
  rows_clean: number;
  duplicates_removed: number;
  empty_removed: number;
  whitespace_fixed: number;
  rows_saved: number;
  reduction_pct: number;
  fuzzy_matching?: { clusters_found?: number; rows_affected?: number };
  schema_validation?: { invalid_rows?: number; rules_count?: number };
  anomaly_detection?: { total_flags?: number };
  normalization?: {
    countries_normalized?: number;
    phones_normalized?: number;
    currencies_normalized?: number;
    dates_normalized?: number;
  };
}

type FileStatus = "pending" | "queued" | "processing" | "completed" | "complete" | "failed" | "error" | "canceled";

interface FileProfile {
  loadable: boolean;
  filename: string;
  size_bytes: number;
  encoding?: string | null;
  delimiter?: string | null;
  headers_detected?: boolean;
  row_count?: number;
  column_count?: number;
  columns?: string[];
  preview_row_count?: number;
  preview?: Record<string, unknown>[];
  manual_options?: Record<string, unknown>;
  error?: string;
}

interface FileItem {
  id: string;
  name: string;
  size?: number;
  status: FileStatus;
  downloadUrl?: string;
  report?: FileReport;
  detection?: FileProfile;
  error?: string;
  localOnly?: boolean;
}

interface AISuggestion {
  column: string;
  issue: string;
  fix: string;
  severity: "high" | "medium" | "low";
}

interface AIAnalysis {
  total_rows: number;
  total_columns: number;
  preview_rows: number;
  suggestions: AISuggestion[];
  summary?: string;
  engine: "gemini" | "heuristic";
}

interface FileSummary {
  total_files: number;
  completed_files: number;
  error_files: number;
  rows_saved: number;
  quality_actions: number;
}

type ExportFormat = "csv" | "xlsx" | "json";

const POLL_INTERVAL_MS = 2500;
const CANCEL_ENDPOINT_TEMPLATE = "/files/{fileId}/cancel";
const pipelinePresets = [
  {
    name: "Sales ops",
    config: {
      fuzzyMatching: true,
      fuzzyColumns: "email,company,phone",
      fuzzyThreshold: 85,
      schemaRules: "required:email, type:number:amount, unique:invoice_id",
      anomalyDetection: true,
      countryColumns: "country,region",
      phoneColumns: "phone,mobile",
      currencyColumns: "amount,total,revenue",
      dateColumns: "created_at,closed_at,paid_at",
      trimWhitespace: true,
      collapseSpaces: true,
    },
  },
  {
    name: "Marketing leads",
    config: {
      fuzzyMatching: true,
      fuzzyColumns: "email,domain,company",
      fuzzyThreshold: 82,
      schemaRules: "required:email, unique:email, type:text:source",
      anomalyDetection: false,
      countryColumns: "country",
      phoneColumns: "phone",
      currencyColumns: "budget",
      dateColumns: "signup_date,created_at",
      trimWhitespace: true,
      collapseSpaces: true,
    },
  },
  {
    name: "Support tickets",
    config: {
      fuzzyMatching: true,
      fuzzyColumns: "email,ticket_id,subject",
      fuzzyThreshold: 88,
      schemaRules: "required:ticket_id, required:email, unique:ticket_id",
      anomalyDetection: true,
      countryColumns: "country",
      phoneColumns: "phone",
      currencyColumns: "refund_amount",
      dateColumns: "created_at,resolved_at",
      trimWhitespace: true,
      collapseSpaces: true,
    },
  },
];


const severityColor: Record<string, string> = {
  high: "text-red-500 bg-red-500/10",
  medium: "text-amber-500 bg-amber-500/10",
  low: "text-sky-400 bg-sky-400/10",
};

export default function DashboardPage() {
  const [files, setFiles]             = useState<FileItem[]>([]);
  const [dragging, setDragging]       = useState(false);
  const [expandedId, setExpandedId]   = useState<string | null>(null);
  const [exportOpen, setExportOpen]   = useState(false);
  const [aiPanel, setAiPanel]         = useState<AIAnalysis | null>(null);
  const [aiLoading, setAiLoading]     = useState(false);
  const [aiCopied, setAiCopied]       = useState(false);
  const [summary, setSummary]         = useState<FileSummary | null>(null);
  const [loading, setLoading]         = useState(true);
  const [loadError, setLoadError]     = useState(false);
  const [toast, setToast]             = useState<DashboardToast | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [utilityFormat, setUtilityFormat] = useState<"original" | "png" | "jpg" | "webp">("original");
  const [utilityQuality, setUtilityQuality] = useState(82);
  const [utilityLoading, setUtilityLoading] = useState(false);
  const [utilityMessage, setUtilityMessage] = useState<string | null>(null);
  const [profilePanel, setProfilePanel] = useState<FileProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalFiles, setTotalFiles] = useState(0);
  const [pipelineConfig, setPipelineConfig] = useState({
    fuzzyMatching: true,
    fuzzyColumns: "",
    fuzzyThreshold: 85,
    schemaRules: "required:email, type:number:amount, unique:invoice_id",
    anomalyDetection: true,
    countryColumns: "country",
    phoneColumns: "phone",
    currencyColumns: "amount,total,price",
    dateColumns: "date,created_at,joined_at",
    trimWhitespace: true,
    collapseSpaces: true,
  });
  const pollingIds = useRef<Set<string>>(new Set());
  const exportRef  = useRef<HTMLDivElement>(null);

  const showToast = useCallback((nextToast: DashboardToast) => {
    setToast(nextToast);
    window.setTimeout(() => setToast(null), 4500);
  }, []);

  const refreshDashboard = useCallback(async (currentPage = page) => {
    setLoading(true);
    setLoadError(false);
    const offset = (currentPage - 1) * pageSize;
    const [filesResult, summaryResult] = await Promise.allSettled([
      apiClient.get<any>(`/files/list?limit=${pageSize}&offset=${offset}`),
      apiClient.get<FileSummary>("/files/summary"),
    ]);

    if (filesResult.status === "fulfilled") {
      const responseData = filesResult.value.data;
      const items = responseData.items || responseData;
      setFiles(items.map((f: any) => ({
        id: f.id.toString(),
        name: f.name ?? f.original_filename ?? f.filename ?? "Untitled file",
        size: typeof f.size === "number" ? f.size : typeof f.size_bytes === "number" ? f.size_bytes : undefined,
        status: f.status,
        downloadUrl: f.download_url,
        report: f.report ?? undefined,
        detection: f.detection ?? undefined,
        error: f.error,
      })));
      setTotalFiles(responseData.total ?? items.length);
    }
    if (summaryResult.status === "fulfilled") {
      setSummary(summaryResult.value.data);
    }
    if (filesResult.status === "rejected" && summaryResult.status === "rejected") {
      setLoadError(true);
    }
    setLoading(false);
  }, [page, pageSize]);

  useEffect(() => {
    refreshDashboard(page);
  }, [page, refreshDashboard]);

  // Auto-poll files that are in queued/processing state
  useEffect(() => {
    const interval = setInterval(async () => {
      const pendingFiles = files.filter(f =>
        (f.status === "pending" || f.status === "queued" || f.status === "processing") && !f.localOnly
      );
      for (const f of pendingFiles) {
        if (pollingIds.current.has(f.id)) continue;
        pollingIds.current.add(f.id);
        try {
          const { data } = await apiClient.get<any>(`/files/${f.id}/status`);
          setFiles(prev => prev.map(pf => pf.id === f.id ? {
            ...pf, status: data.status, downloadUrl: data.download_url,
            report: data.report, detection: data.detection, error: data.error,
          } : pf));
        } catch { /* ignore transient */ } finally {
          pollingIds.current.delete(f.id);
        }
      }
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [files]);

  // Close export dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) setExportOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleDelete = async (fileId: string) => {
    if (deleteConfirmId !== fileId) {
      setDeleteConfirmId(fileId);
      showToast({ tone: "info", message: "Click delete again to remove this file." });
      window.setTimeout(() => setDeleteConfirmId(current => current === fileId ? null : current), 5000);
      return;
    }
    setDeleteConfirmId(null);
    trackEvent("feature_used", { feature_name: "delete_file" });
    try {
      await apiClient.delete(`/files/${fileId}`);
      setFiles(prev => prev.filter(f => f.id !== fileId));
      showToast({ tone: "success", message: "Your file was deleted." });
    } catch {
      showToast({ tone: "error", message: "We could not delete your file. Retry in a moment." });
    }
  };

  const formatSize = (bytes?: number) => {
    if (typeof bytes !== "number" || !Number.isFinite(bytes) || bytes < 0) return "Size unavailable";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const splitColumns = (value: string) =>
    value.split(",").map(item => item.trim()).filter(Boolean);

  const parseSchemaRules = () => {
    const raw = pipelineConfig.schemaRules.trim();
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return raw.split(",").map(item => item.trim()).filter(Boolean).map((item) => {
        const [kind, value, column] = item.split(":").map(part => part.trim()).filter(Boolean);
        if (kind === "required" && value) return { column: value, not_null: true };
        if (kind === "unique" && value) return { column: value, unique: true };
        if (kind === "type" && value && column) {
          const normalizedType = value === "number" ? "float" : value;
          return { column, type: normalizedType };
        }
        return null;
      }).filter(Boolean);
    }
  };

  const buildPipelineConfig = () => ({
    basic_cleaning: {
      drop_empty_rows: true,
      trim_whitespace: pipelineConfig.trimWhitespace,
      collapse_spaces: pipelineConfig.collapseSpaces,
      drop_duplicates: true,
    },
    fuzzy_matching: {
      enabled: pipelineConfig.fuzzyMatching,
      columns: splitColumns(pipelineConfig.fuzzyColumns),
      threshold: pipelineConfig.fuzzyThreshold,
    },
    schema_validation: {
      rules: parseSchemaRules(),
    },
    anomaly_detection: {
      enabled: pipelineConfig.anomalyDetection,
      numeric_columns: splitColumns(pipelineConfig.currencyColumns),
      categorical_columns: splitColumns(pipelineConfig.countryColumns),
    },
    normalization: {
      countries: splitColumns(pipelineConfig.countryColumns),
      phones: splitColumns(pipelineConfig.phoneColumns).map(column => ({ column, default_country_code: "+1" })),
      currencies: splitColumns(pipelineConfig.currencyColumns),
      dates: splitColumns(pipelineConfig.dateColumns),
    },
  });

  const analyzeFile = async (fileInput: File) => {
    setProfileLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", fileInput);
      const { data } = await uploadFile<FileProfile>("/files/analyze", formData);
      setProfilePanel(data);
      return data;
    } finally {
      setProfileLoading(false);
    }
  };

  const handleCancel = async (fileId: string) => {
    trackEvent("feature_used", { feature_name: "cancel_file_job" });
    try {
      await apiClient.post(CANCEL_ENDPOINT_TEMPLATE.replace("{fileId}", fileId));
      setFiles(prev => prev.map(f => f.id === fileId ? { ...f, status: "canceled" } : f));
      showToast({ tone: "success", message: "Processing was canceled and temp files were cleaned." });
    } catch {
      showToast({ tone: "error", message: "We could not cancel that job. Refresh and retry." });
    }
  };

  const handleFiles = async (fileList: FileList) => {
    const newFiles: FileItem[] = Array.from(fileList).map(f => ({
      id: crypto.randomUUID(),
      name: f.name,
      size: f.size,
      status: "pending" as const,
      localOnly: true,
    }));
    setFiles(prev => [...newFiles, ...prev]);
    trackEvent("feature_used", { feature_name: "file_upload" });

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      const tempId = newFiles[i].id;
      try {
        const profile = await analyzeFile(file);
        if (!profile.loadable) {
          throw new Error("File needs manual encoding, delimiter, or header options before processing.");
        }
        const formData = new FormData();
        formData.append("file", file);
        formData.append("config_json", JSON.stringify(buildPipelineConfig()));
        const { data } = await uploadFile<{ id: number; status: FileItem["status"]; detection?: FileProfile }>("/files/upload", formData);
        setFiles(prev => prev.map(f => f.id === tempId ? {
          ...f, id: data.id.toString(), status: data.status, detection: data.detection, localOnly: false,
        } : f));
        showToast({ tone: "success", message: `${file.name} is pending cleanup.` });
      } catch (e: any) {
        setFiles(prev => prev.map(f => f.id === tempId ? { ...f, status: "failed", error: e.message } : f));
        showToast({ tone: "error", message: `We could not read ${file.name}. Check that it is CSV, JSON, XLSX, or XLS.` });
      }
    }
  };

  // Export GET /files/export?format=csv|xlsx|json
  const handleExport = async (format: ExportFormat) => {
    setExportOpen(false);
    trackEvent("feature_used", { feature_name: "export_files", format });
    try {
      await downloadFile(`/files/export?format=${format}`, `filecleaner_export.${format}`);
      showToast({ tone: "success", message: `Your file history export started as ${format.toUpperCase()}.` });
    } catch {
      showToast({ tone: "error", message: "We could not export your file history. Retry from the export menu." });
    }
  };

  // AI Analyze — POST /files/ai-analyze with a file
  const handleAIAnalyze = async (fileInput: File) => {
    setAiLoading(true);
    setAiPanel(null);
    trackEvent("feature_used", { feature_name: "ai_analyze_file" });
    try {
      const formData = new FormData();
      formData.append("file", fileInput);
      const { data } = await uploadFile<AIAnalysis>("/files/ai-analyze", formData);
      setAiPanel(data);
      showToast({ tone: "success", message: `We checked ${fileInput.name} for cleanup opportunities.` });
    } catch (e: any) {
      showToast({ tone: "error", message: e.message || "We could not check this file. Retry with CSV, JSON, XLSX, or XLS." });
    } finally {
      setAiLoading(false);
    }
  };

  const openAIAnalyze = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".csv,.json,.xlsx,.xls";
    input.onchange = e => {
      const f = (e.target as HTMLInputElement).files?.[0];
      if (f) handleAIAnalyze(f);
    };
    input.click();
  };

  const handleUtilityFile = async (fileInput: File) => {
    setUtilityLoading(true);
    setUtilityMessage(null);
    trackEvent("feature_used", { feature_name: "file_utility_process", format: utilityFormat, quality: utilityQuality });
    try {
      const formData = new FormData();
      formData.append("file", fileInput);
      const params = new URLSearchParams({ quality: String(utilityQuality) });
      if (utilityFormat !== "original") params.set("output_format", utilityFormat);
      const { filename } = await uploadAndDownloadFile(`/files/utility?${params.toString()}`, formData, `cleaned-${fileInput.name}`);
      setUtilityMessage(`Cleaned and downloaded ${filename}`);
      showToast({ tone: "success", message: `Your file was cleaned and downloaded as ${filename}.` });
    } catch (e: any) {
      showToast({ tone: "error", message: e.detail || e.message || "We could not clean this file. Retry with PNG, JPG, WEBP, HEIC, SVG, or PDF." });
    } finally {
      setUtilityLoading(false);
    }
  };

  const openFileUtility = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".png,.jpg,.jpeg,.webp,.heic,.heif,.svg,.pdf";
    input.onchange = e => {
      const f = (e.target as HTMLInputElement).files?.[0];
      if (f) handleUtilityFile(f);
    };
    input.click();
  };

  const statusIcon = (status: string) => {
    if (status === "pending" || status === "queued") return <Clock className="text-amber-500" size={16} />;
    if (status === "processing") return <RefreshCw className="animate-spin text-indigo-500" size={16} />;
    if (status === "completed" || status === "complete") return <CheckCircle className="text-emerald-500" size={16} />;
    if (status === "canceled") return <X className="text-slate-400" size={16} />;
    return <AlertCircle className="text-red-500" size={16} />;
  };

  const statusLabel: Record<string, string> = {
    pending: "Pending",
    queued: "Queued",
    processing: "Cleaning...",
    completed: "Ready",
    complete: "Ready",
    failed: "Needs attention",
    error: "Needs attention",
    canceled: "Canceled",
  };

  return (
    <div className="dashboard-motion max-w-5xl mx-auto py-6 md:py-10 px-0 sm:px-4">
      <ActionToast toast={toast} onDismiss={() => setToast(null)} />
      {/* Header */}
      <div className="flex items-center justify-between mb-8 gap-4 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2" style={{ color: "var(--color-text)" }}>
            Data Cleaning Hub
          </h1>
          <p className="text-sm opacity-60" style={{ color: "var(--color-text)" }}>
            Smart normalization for CSV and Excel datasets. Up to 100MB.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* AI Analyze Button */}
          <button
            onClick={openAIAnalyze}
            disabled={aiLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all"
            style={{
              background: "linear-gradient(135deg, var(--color-primary), #6366f1)",
              color: "#000",
              opacity: aiLoading ? 0.7 : 1
            }}
          >
            {aiLoading ? <InlineSpinner /> : <Brain size={14} />}
            <span>{aiLoading ? "Checking file" : "Check file quality"}</span>
          </button>

          <button
            onClick={openFileUtility}
            disabled={utilityLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all"
            style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)", border: "1px solid var(--color-border)", opacity: utilityLoading ? 0.7 : 1 }}
            title="Strip metadata, compress images, or convert supported files"
          >
            {utilityLoading ? <InlineSpinner /> : <ImageIcon size={14} />}
            <span>{utilityLoading ? "Cleaning file" : "Clean image or PDF"}</span>
          </button>

          {/* Export Dropdown */}
          <div className="relative" ref={exportRef}>
            <button
              onClick={() => setExportOpen(!exportOpen)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all"
              style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)", border: "1px solid var(--color-border)" }}
            >
              <Download size={14} />
              <span>Export history</span>
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
        </div>
      </div>

      <div className="mb-8">
        <DashboardPlanPanel
          product={dashboardProduct}
          quotas={[
            { label: "Max upload size", used: 0 },
            { label: "Retention", used: 0 },
            { label: "Schema rules", used: pipelineConfig.schemaRules.trim() ? parseSchemaRules().length : 0 },
          ]}
        />
      </div>

      {loadError && (
        <div className="mb-8">
          <InlineErrorState
            title="We could not load your files"
            description="Your dashboard data did not load. Retry now, and contact support if it keeps happening."
            onRetry={refreshDashboard}
          />
        </div>
      )}

      {loading && files.length === 0 && <DashboardSkeleton rows={3} />}

      {!loading && !loadError && files.length === 0 && (
        <WelcomeSteps
          title="Clean your first file"
          description="Start with one dataset and see clean rows, duplicates removed, and empty rows found before you export."
          steps={[
            "Upload a CSV, JSON, XLSX, or XLS file.",
            "Review clean rows, duplicates removed, and empty rows found.",
            "Download the cleaned file or export your cleanup history.",
          ]}
          actionLabel="Upload your first file"
          onAction={() => document.getElementById("filecleaner-dropzone")?.click()}
        />
      )}

      {!loading && (
      <>
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          {[
            { label: "Files ready", value: summary.completed_files.toLocaleString(), tone: "text-emerald-500" },
            { label: "Rows cleaned", value: summary.rows_saved.toLocaleString(), tone: "text-[var(--color-primary)]" },
            { label: "Cleanup actions", value: summary.quality_actions.toLocaleString(), tone: "text-sky-400" },
            { label: "Files needing review", value: summary.error_files.toLocaleString(), tone: summary.error_files ? "text-red-500" : "text-emerald-500" },
          ].map(stat => (
            <div key={stat.label} className="p-4 rounded-xl" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
              <p className="text-[10px] uppercase font-bold tracking-wider opacity-50 mb-1">{stat.label}</p>
              <p className={`text-xl font-mono font-bold ${stat.tone}`}>{stat.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="mb-8 p-4 rounded-xl"
        style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 mb-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider opacity-50 mb-1">Pipeline controls</p>
            <p className="text-sm opacity-70">Preview first 100 rows, then run basic cleaning, fuzzy matching, schema validation, anomaly detection, and normalization.</p>
          </div>
          {profileLoading && <InlineSpinner />}
        </div>

        <div className="mb-4 flex flex-wrap gap-2">
          {pipelinePresets.map((preset) => (
            <button
              key={preset.name}
              type="button"
              onClick={() => setPipelineConfig(preset.config)}
              className="rounded-md border border-white/10 px-3 py-2 text-xs font-semibold transition hover:border-[var(--color-primary)]"
              style={{ color: "var(--color-text)", backgroundColor: "var(--color-surface-raised)" }}
            >
              {preset.name}
            </button>
          ))}
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <div className="flex flex-wrap gap-4 p-2 rounded-lg bg-black/10 mb-2">
              <label className="flex items-center gap-2 text-xs select-none cursor-pointer">
                <input
                  type="checkbox"
                  checked={pipelineConfig.trimWhitespace}
                  onChange={e => setPipelineConfig(prev => ({ ...prev, trimWhitespace: e.target.checked }))}
                />
                <span>Trim whitespace</span>
              </label>
              <label className="flex items-center gap-2 text-xs select-none cursor-pointer">
                <input
                  type="checkbox"
                  checked={pipelineConfig.collapseSpaces}
                  onChange={e => setPipelineConfig(prev => ({ ...prev, collapseSpaces: e.target.checked }))}
                />
                <span>Collapse double spaces</span>
              </label>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={pipelineConfig.fuzzyMatching}
                onChange={e => setPipelineConfig(prev => ({ ...prev, fuzzyMatching: e.target.checked }))}
              />
              <span>Fuzzy matching</span>
            </label>
            <div className="grid grid-cols-[1fr_96px] gap-2">
              <label className="text-xs">
                <span className="block opacity-50 mb-1">Fuzzy columns</span>
                <input
                  value={pipelineConfig.fuzzyColumns}
                  onChange={e => setPipelineConfig(prev => ({ ...prev, fuzzyColumns: e.target.value }))}
                  placeholder="company,name,email"
                  className="input-field px-3 py-2 w-full"
                />
              </label>
              <label className="text-xs">
                <span className="block opacity-50 mb-1">Threshold</span>
                <input
                  type="number"
                  min={50}
                  max={100}
                  value={pipelineConfig.fuzzyThreshold}
                  onChange={e => setPipelineConfig(prev => ({ ...prev, fuzzyThreshold: Math.max(50, Math.min(100, Number(e.target.value) || 85)) }))}
                  className="input-field px-3 py-2 w-full"
                />
              </label>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={pipelineConfig.anomalyDetection}
                onChange={e => setPipelineConfig(prev => ({ ...prev, anomalyDetection: e.target.checked }))}
              />
              <span>Anomaly detection</span>
            </label>
            <label className="text-xs block">
              <span className="block opacity-50 mb-1">Schema validation</span>
              <textarea
                value={pipelineConfig.schemaRules}
                onChange={e => setPipelineConfig(prev => ({ ...prev, schemaRules: e.target.value }))}
                className="input-field px-3 py-2 w-full min-h-20 font-mono"
                placeholder="required:email, type:number:amount, unique:invoice_id"
                spellCheck={false}
              />
            </label>
          </div>

          <div className="space-y-3">
            <p className="text-sm font-medium">Normalization</p>
            {[
              ["Country columns", "countryColumns"],
              ["Phone columns", "phoneColumns"],
              ["Currency columns", "currencyColumns"],
              ["Date columns", "dateColumns"],
            ].map(([label, key]) => (
              <label key={key} className="text-xs block">
                <span className="block opacity-50 mb-1">{label}</span>
                <input
                  value={pipelineConfig[key as keyof typeof pipelineConfig] as string}
                  onChange={e => setPipelineConfig(prev => ({ ...prev, [key]: e.target.value }))}
                  className="input-field px-3 py-2 w-full"
                />
              </label>
            ))}
          </div>
        </div>
      </div>

      {profilePanel && (
        <div className="mb-8 p-4 rounded-xl overflow-hidden"
          style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
          <div className="flex items-center justify-between gap-4 mb-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider opacity-50 mb-1">Preview first 100 rows</p>
              <p className="text-sm opacity-70">
                {profilePanel.loadable
                  ? `${profilePanel.row_count?.toLocaleString() ?? 0} rows, ${profilePanel.column_count ?? 0} columns, ${profilePanel.encoding ?? "auto"}${profilePanel.delimiter ? `, delimiter "${profilePanel.delimiter}"` : ""}`
                  : profilePanel.error || "Manual options required"}
              </p>
            </div>
            <button
              onClick={() => setProfilePanel(null)}
              className="p-2 rounded-lg hover:bg-black/10 transition-colors"
              title="Close preview"
            >
              <X size={16} />
            </button>
          </div>
          {profilePanel.preview && profilePanel.preview.length > 0 && (
            <div className="dashboard-table-scroll max-h-72 border border-[var(--color-border)] rounded-lg">
              <table className="min-w-full text-xs">
                <thead className="sticky top-0" style={{ backgroundColor: "var(--color-surface)" }}>
                  <tr>
                    {(profilePanel.columns ?? Object.keys(profilePanel.preview[0])).slice(0, 8).map(column => (
                      <th key={column} className="text-left px-3 py-2 font-bold border-b border-[var(--color-border)]">{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {profilePanel.preview.slice(0, 12).map((row, index) => (
                    <tr key={index} className="border-b border-[var(--color-border)] last:border-0">
                      {(profilePanel.columns ?? Object.keys(row)).slice(0, 8).map(column => (
                        <td key={column} className="px-3 py-2 whitespace-nowrap opacity-70">{String(row[column] ?? "")}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <div className="mb-8 p-4 rounded-xl flex flex-col md:flex-row md:items-end gap-4"
        style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
        <div className="flex-1">
          <p className="text-xs font-bold uppercase tracking-wider opacity-50 mb-1">Your file utility</p>
          <p className="text-sm opacity-70">Strip metadata, compress images, or convert PNG, JPG, WEBP, HEIC, SVG, and PDF files.</p>
          {utilityMessage && <p className="text-xs text-emerald-500 mt-2">{utilityMessage}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs">
            <span className="block opacity-50 mb-1">Output</span>
            <select value={utilityFormat} onChange={e => setUtilityFormat(e.target.value as typeof utilityFormat)} className="input-field px-3 py-2">
              <option value="original">Keep format</option>
              <option value="png">PNG</option>
              <option value="jpg">JPG</option>
              <option value="webp">WEBP</option>
            </select>
          </label>
          <label className="text-xs w-28">
            <span className="block opacity-50 mb-1">Quality</span>
            <input type="number" min={1} max={95} value={utilityQuality}
              onChange={e => setUtilityQuality(Math.max(1, Math.min(95, Number(e.target.value) || 82)))}
              className="input-field px-3 py-2" />
          </label>
          <button onClick={openFileUtility} disabled={utilityLoading} className="btn-primary flex items-center gap-2">
            {utilityLoading ? <InlineSpinner /> : <Download size={14} />}
            {utilityLoading ? "Cleaning file" : "Clean selected file"}
          </button>
        </div>
      </div>

      {/* AI Analysis Panel */}
      {aiPanel && (
        <div className="mb-8 rounded-2xl overflow-hidden animate-in fade-in slide-in-from-top-4 duration-300"
          style={{ border: "1px solid var(--color-border)", backgroundColor: "var(--color-surface)" }}>
          <div className="flex items-center justify-between p-5 border-b border-[var(--color-border)] bg-black/5">
            <div className="flex items-center gap-3">
              <Brain size={18} className="text-[var(--color-primary)]" />
              <div>
                <h3 className="text-sm font-bold">AI Cleanup Analysis</h3>
                <p className="text-[10px] opacity-50">
                  {aiPanel.total_rows.toLocaleString()} rows × {aiPanel.total_columns} columns
                  — Engine: <span className="font-bold">{aiPanel.engine === "gemini" ? "✨ Gemini" : "Heuristic"}</span>
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => { navigator.clipboard.writeText(JSON.stringify(aiPanel.suggestions, null, 2)); setAiCopied(true); setTimeout(() => setAiCopied(false), 2000); }}
                className="p-1.5 rounded-lg hover:bg-black/10 transition-colors"
                title="Copy as JSON"
              >
                {aiCopied ? <Check size={16} className="text-emerald-500" /> : <Copy size={16} className="opacity-50" />}
              </button>
              <button onClick={() => setAiPanel(null)} className="p-1.5 rounded-lg hover:bg-black/10 transition-colors">
                <X size={16} className="opacity-50" />
              </button>
            </div>
          </div>

          {aiPanel.summary && (
            <div className="px-5 py-3 text-sm opacity-70 border-b border-[var(--color-border)] italic">
              {aiPanel.summary}
            </div>
          )}

          <div className="p-5 space-y-3">
            {aiPanel.suggestions.length === 0 ? (
              <div className="text-center py-6 text-sm opacity-40">
                <CheckCircle size={24} className="mx-auto mb-2 text-emerald-500 opacity-100" />
                No cleanup issues found in your file.
              </div>
            ) : (
              aiPanel.suggestions.map((s, i) => (
                <div key={i} className="flex items-start gap-3 p-3 rounded-xl"
                  style={{ backgroundColor: "rgba(0,0,0,0.04)", border: "1px solid var(--color-border)" }}>
                  <span className={`mt-0.5 text-[10px] font-bold px-2 py-0.5 rounded uppercase shrink-0 ${severityColor[s.severity] || "text-gray-400 bg-gray-400/10"}`}>
                    {s.severity}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold mb-0.5 truncate">{s.column}</p>
                    <p className="text-xs opacity-60">{s.issue}</p>
                    <p className="text-xs text-[var(--color-primary)] mt-1">Suggested fix: {s.fix}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Drop Zone */}
      <div
        id="filecleaner-dropzone"
        className="relative rounded-2xl p-16 text-center cursor-pointer transition-all duration-300 mb-10 group"
        style={{
          backgroundColor: dragging ? "rgba(var(--color-primary-rgb), 0.05)" : "var(--color-surface)",
          border: `2px dashed ${dragging ? "var(--color-primary)" : "var(--color-border)"}`,
        }}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => {
          const input = document.createElement("input");
          input.type = "file";
          input.accept = ".csv,.json,.xlsx,.xls";
          input.multiple = true;
          input.onchange = e => { const f = (e.target as HTMLInputElement).files; if (f) handleFiles(f); };
          input.click();
        }}
      >
        <div className="mx-auto w-16 h-16 rounded-full bg-black/5 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
          <FileText size={32} className="text-[var(--color-primary)]" />
        </div>
        <p className="text-lg font-semibold mb-2" style={{ color: "var(--color-text)" }}>
          Drop your file here or click to upload
        </p>
        <p className="text-xs opacity-50" style={{ color: "var(--color-text)" }}>
          CSV, JSON, XLSX, or XLS up to 100MB. We clean it in the background.
        </p>
      </div>

      {/* File List */}
      <div className="space-y-4">
        {files.map(file => {
          const isExpanded = expandedId === file.id;
          const isPending  = file.status === "pending" || file.status === "queued" || file.status === "processing";
          const isComplete = file.status === "completed" || file.status === "complete";
          const isFailed = file.status === "failed" || file.status === "error";
          return (
            <div key={file.id} className="rounded-xl overflow-hidden transition-all duration-200"
              style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
              <div
                className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer hover:bg-black/5"
                onClick={() => file.report && setExpandedId(isExpanded ? null : file.id)}
              >
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div className="p-2 rounded-lg bg-black/5">{statusIcon(file.status)}</div>
                  <div className="truncate">
                    <h3 className="text-sm font-medium truncate" style={{ color: "var(--color-text)" }}>{file.name}</h3>
                    <p className="text-xs opacity-50" style={{ color: "var(--color-text)" }}>{formatSize(file.size)}</p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {/* Status Badge */}
                  <div className="flex items-center gap-2">
                    {isPending && (
                      <div className="flex items-center gap-1.5">
                        <div className="w-24 h-1.5 rounded-full bg-black/10 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-[var(--color-primary)] transition-all"
                            style={{ width: file.status === "processing" ? "65%" : "15%", animation: "pulse 1.5s ease-in-out infinite" }}
                          />
                        </div>
                        <span className="text-[10px] font-bold text-[var(--color-primary)]">{statusLabel[file.status]}</span>
                      </div>
                    )}
                    {!isPending && (
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded ${
                        isComplete ? "bg-emerald-500/10 text-emerald-500" :
                        isFailed ? "bg-red-500/10 text-red-500" :
                        file.status === "canceled" ? "bg-slate-500/10 text-slate-500" : "bg-black/5"
                      }`}>
                        {statusLabel[file.status]}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {isPending && !file.localOnly && (
                      <button
                        onClick={e => { e.stopPropagation(); handleCancel(file.id); }}
                        className="p-2 rounded-lg hover:bg-amber-500/10 text-amber-600 transition-colors"
                        title="Cancel job"
                      >
                        <X size={18} />
                      </button>
                    )}
                    {file.downloadUrl && (
                      <a
                        href={getApiUrl(file.downloadUrl)}
                        className="p-2 rounded-lg hover:bg-[var(--color-primary)]/10 text-[var(--color-primary)] transition-colors"
                        title="Download Cleaned File"
                        onClick={e => e.stopPropagation()}
                      >
                        <Download size={18} />
                      </a>
                    )}
                    <button
                      onClick={e => { e.stopPropagation(); handleDelete(file.id); }}
                      className="p-2 rounded-lg hover:bg-red-500/10 text-red-500/60 hover:text-red-500 transition-colors"
                    >
                      <Trash2 size={18} />
                    </button>
                    {file.report && (isExpanded ? <ChevronUp size={20} className="opacity-30" /> : <ChevronDown size={20} className="opacity-30" />)}
                  </div>
                </div>
              </div>

              {/* Report Panel */}
              {isExpanded && file.report && (
                <div className="p-6 border-t border-[var(--color-border)] bg-black/5 animate-in fade-in slide-in-from-top-2 duration-300">
                  <div className="flex items-center gap-3 mb-6 p-4 rounded-xl"
                    style={{ backgroundColor: "rgba(var(--color-primary-rgb), 0.08)", border: "1px solid rgba(var(--color-primary-rgb), 0.15)" }}>
                    <Zap size={20} className="text-[var(--color-primary)]" />
                    <div>
                      <p className="text-sm font-bold text-[var(--color-primary)]">
                        {file.report.reduction_pct > 0
                          ? `${file.report.reduction_pct}% smaller file with ${file.report.rows_saved.toLocaleString()} rows cleaned`
                          : "Your file was already clean."}
                      </p>
                      <p className="text-xs opacity-60">Your cleaned file is ready to download.</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 mb-4 text-[var(--color-primary)]">
                    <Info size={16} />
                    <h4 className="text-xs font-bold uppercase tracking-wider">Your cleanup report</h4>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    {[
                      { label: "Rows found",   value: file.report.rows_original.toLocaleString(),    color: "text-[var(--color-text)]" },
                      { label: "Clean rows",   value: file.report.rows_clean.toLocaleString(),        color: "text-emerald-500" },
                      { label: "Duplicates",   value: file.report.duplicates_removed.toLocaleString(), color: "text-indigo-400" },
                      { label: "Empty rows",   value: file.report.empty_removed.toLocaleString(),     color: "text-amber-500" },
                      { label: "Text fixes",   value: file.report.whitespace_fixed.toLocaleString(),  color: "text-sky-400" },
                    ].map(stat => (
                      <div key={stat.label} className="p-3 rounded-lg bg-white/5 border border-white/5">
                        <p className="text-[10px] uppercase font-bold opacity-40 mb-1">{stat.label}</p>
                        <p className={`text-lg font-mono font-bold ${stat.color}`}>{stat.value}</p>
                      </div>
                    ))}
                  </div>

                  {file.report.reduction_pct > 0 && (
                    <div className="mt-4 flex items-center gap-2 text-xs text-emerald-500">
                      <TrendingDown size={14} />
                      <span>{file.report.reduction_pct}% fewer rows after cleaning</span>
                    </div>
                  )}

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                    {[
                      { label: "Fuzzy clusters", value: file.report.fuzzy_matching?.clusters_found ?? 0 },
                      { label: "Schema invalid rows", value: file.report.schema_validation?.invalid_rows ?? 0 },
                      { label: "Anomaly flags", value: file.report.anomaly_detection?.total_flags ?? 0 },
                      {
                        label: "Normalization edits",
                        value: (
                          (file.report.normalization?.countries_normalized ?? 0) +
                          (file.report.normalization?.phones_normalized ?? 0) +
                          (file.report.normalization?.currencies_normalized ?? 0) +
                          (file.report.normalization?.dates_normalized ?? 0)
                        ),
                      },
                    ].map(stat => (
                      <div key={stat.label} className="p-3 rounded-lg bg-white/5 border border-white/5">
                        <p className="text-[10px] uppercase font-bold opacity-40 mb-1">{stat.label}</p>
                        <p className="text-lg font-mono font-bold text-[var(--color-primary)]">{stat.value.toLocaleString()}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Error Message */}
              {isFailed && file.error && (
                <div className="px-6 py-4 border-t border-red-500/20 bg-red-500/5">
                  <p className="text-xs text-red-500">{file.error}</p>
                </div>
              )}
            </div>
          );
        })}

        {totalFiles > pageSize && (
          <div className="flex items-center justify-between pt-4 pb-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/5 border border-white/10 hover:bg-white/10 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="text-xs opacity-65">
              Page {page} of {Math.ceil(totalFiles / pageSize)}
            </span>
            <button
              onClick={() => setPage(p => Math.min(Math.ceil(totalFiles / pageSize), p + 1))}
              disabled={page >= Math.ceil(totalFiles / pageSize)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/5 border border-white/10 hover:bg-white/10 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        )}

        {files.length === 0 && (
          <DashboardEmptyState
            icon={<Sparkles size={24} />}
            title="Upload your first file"
            description="Clean one file to see rows cleaned, duplicates removed, and empty rows found."
            actionLabel="Upload a file"
            onAction={() => document.getElementById("filecleaner-dropzone")?.click()}
          />
        )}
      </div>
      </>
      )}
    </div>
  );
}
