"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { apiClient, downloadFile, getProduct, trackEvent, type PlanSlug } from "@devforge/core";
import {
  ActionToast,
  DashboardPlanPanel,
  DashboardEmptyState,
  DashboardSkeleton,
  InlineErrorState,
  InlineSpinner,
  WelcomeSteps,
  getSettingsErrorMessage,
  type DashboardToast,
} from "@devforge/ui";
import { 
  Activity, Trash2, RefreshCcw, Copy, Check, Search, Code,
  Database, X, ChevronRight, Send, AlertCircle, Download, ChevronDown
} from "lucide-react";

const dashboardProduct = getProduct("webhookmonitor");

interface WebhookRequest {
  id: number;
  event_id?: string;
  endpoint_id?: number;
  method: string;
  path: string;
  headers: Record<string, string>;
  body: string;
  query_params?: Record<string, string>;
  ip_address?: string;
  received_at: string;
  retry_count: number;
  last_retry_status: number | null;
  forward_error?: string;
  signature_valid?: boolean | null;
  signature_error?: string;
  signature_provider?: string;
  replay_of_request_id?: number | null;
  replay_target_url?: string;
  replay_status?: string;
  auto_retry_enabled: boolean;
  schema_valid?: boolean | null;
  schema_error?: string;
}

interface WebhookEndpoint {
  id: number;
  uuid: string;
  name: string;
  endpoint_url: string;
  methods: string[];
  created_at?: string | null;
  is_active: boolean;
}

const methodColors: Record<string, string> = {
  GET: "#10B981", POST: "#6366F1", PUT: "#F59E0B", DELETE: "#EF4444", PATCH: "#8B5CF6",
};

type ExportFormat = "csv" | "xlsx" | "json";
type EventExportFormat = "curl" | "postman" | "har" | "openapi";
type LogStatusFilter = "all" | "failed" | "successful" | "pending" | "auto_retry";
type ReplayMode = "exact" | "modified" | "alternate";

const eventExportQueries: Record<EventExportFormat, string> = {
  curl: "/export?format=curl",
  postman: "/export?format=postman",
  har: "/export?format=har",
  openapi: "/export?format=openapi",
};

interface WebhookSummary {
  total_requests: number;
  recent_24h: number;
  retry_pressure: number;
  failed_forwards: number;
  auto_retry_enabled: number;
}

interface ProfilePlanResponse {
  plans_by_product?: { webhookmonitor?: PlanSlug };
  dashboard_limits_by_product?: {
    webhookmonitor?: Partial<Record<PlanSlug, { max_endpoints?: number }>>;
  };
}

interface DiffItem {
  path: string;
  value?: unknown;
  old_value?: unknown;
  new_value?: unknown;
}

interface DiffBucket {
  added: DiffItem[];
  removed: DiffItem[];
  changed: DiffItem[];
}

interface RequestDiff {
  request_id: number;
  base_request_id: number;
  headers: DiffBucket;
  body: DiffBucket;
}

interface SchemaValidationResult {
  request_id: number;
  valid: boolean;
  errors: Array<{ path: string; message: string; validator: string }>;
}

interface ReplayResponse {
  status: "success" | "failed";
  error?: string;
}

export default function DashboardPage() {
  const [requests, setRequests]       = useState<WebhookRequest[]>([]);
  const [endpoints, setEndpoints]     = useState<WebhookEndpoint[]>([]);
  const [selected, setSelected]       = useState<WebhookRequest | null>(null);
  const [endpointUrl, setEndpointUrl] = useState("");
  const [endpointForm, setEndpointForm] = useState({ name: "", methods: "POST" });
  const [creatingEndpoint, setCreatingEndpoint] = useState(false);
  const [deletingEndpointId, setDeletingEndpointId] = useState<number | null>(null);
  const [search, setSearch]           = useState("");
  const [jsonSearchPath, setJsonSearchPath] = useState("");
  const [jsonSearchEquals, setJsonSearchEquals] = useState("");
  const [methodFilter, setMethodFilter] = useState("");
  const [providerFilter, setProviderFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [copied, setCopied]           = useState(false);
  const [retryPayload, setRetryPayload] = useState("");
  const [replayMode, setReplayMode] = useState<ReplayMode>("exact");
  const [replayTargetUrl, setReplayTargetUrl] = useState("");
  const [replayHeaders, setReplayHeaders] = useState("{}");
  const [isReplaying, setIsReplaying] = useState(false);
  const [isEditingPayload, setIsEditingPayload] = useState(false);
  const [isRetrying, setIsRetrying]   = useState(false);
  const [isDiffing, setIsDiffing]     = useState(false);
  const [diffResult, setDiffResult]   = useState<RequestDiff | null>(null);
  const [schemaText, setSchemaText]   = useState('{\n  "type": "object"\n}');
  const [isValidatingSchema, setIsValidatingSchema] = useState(false);
  const [schemaResult, setSchemaResult] = useState<SchemaValidationResult | null>(null);
  const [exportOpen, setExportOpen]   = useState(false);
  const [eventExporting, setEventExporting] = useState<EventExportFormat | null>(null);
  const [summary, setSummary]         = useState<WebhookSummary | null>(null);
  const [endpointLimit, setEndpointLimit] = useState(1);
  const [endpointPlan, setEndpointPlan] = useState<PlanSlug>("free");
  const [logStatus, setLogStatus]     = useState<LogStatusFilter>("all");
  const [loading, setLoading]         = useState(true);
  const [loadError, setLoadError]     = useState(false);
  const [toast, setToast]             = useState<DashboardToast | null>(null);
  const [clearConfirm, setClearConfirm] = useState(false);
  const [hasServerSearch, setHasServerSearch] = useState(false);
  const intervalRef                   = useRef<NodeJS.Timeout | null>(null);
  const exportRef                     = useRef<HTMLDivElement>(null);
  const clearConfirmRef               = useRef(false);
  const historyClearedRef             = useRef(false);
  const refreshGenerationRef          = useRef(0);
  const editedPayloadInvalid = isEditingPayload && (() => {
    try { JSON.parse(retryPayload); return false; } catch { return true; }
  })();

  const showToast = useCallback((nextToast: DashboardToast) => {
    setToast(nextToast);
    window.setTimeout(() => setToast(null), 4500);
  }, []);

  const refreshWebhooks = useCallback(async (showLoading = true) => {
    const refreshGeneration = refreshGenerationRef.current;
    if (showLoading) setLoading(true);
    setLoadError(false);
    const [configResult, endpointResult, summaryResult, logsResult, profileResult] = await Promise.allSettled([
      apiClient.get<{ endpoint_url: string }>("/webhooks/config"),
      apiClient.get<WebhookEndpoint[]>("/webhooks/endpoints"),
      apiClient.get<WebhookSummary>("/webhooks/summary"),
      apiClient.get<WebhookRequest[]>(`/webhooks/logs?status=${logStatus}`),
      apiClient.get<ProfilePlanResponse>("/auth/profile"),
    ]);

    if (refreshGeneration !== refreshGenerationRef.current) {
      if (showLoading) setLoading(false);
      return;
    }

    if (configResult.status === "fulfilled") setEndpointUrl(configResult.value.data.endpoint_url);
    if (endpointResult.status === "fulfilled") setEndpoints(endpointResult.value.data);
    if (summaryResult.status === "fulfilled" && !historyClearedRef.current) {
      setSummary(summaryResult.value.data);
    }
    if (logsResult.status === "fulfilled") {
      const nextRequests = logsResult.value.data;
      if (!historyClearedRef.current && !hasServerSearch) setRequests(nextRequests);
    }
    if (profileResult.status === "fulfilled") {
      const nextPlan = profileResult.value.data.plans_by_product?.webhookmonitor || "free";
      const nextLimit = profileResult.value.data.dashboard_limits_by_product?.webhookmonitor?.[nextPlan]?.max_endpoints;
      setEndpointPlan(nextPlan);
      if (typeof nextLimit === "number") setEndpointLimit(nextLimit);
    }
    if (
      configResult.status === "rejected" &&
      endpointResult.status === "rejected" &&
      summaryResult.status === "rejected" &&
      logsResult.status === "rejected"
    ) {
      setLoadError(true);
    }
    if (showLoading) setLoading(false);
  }, [logStatus, hasServerSearch]);

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
      setReplayMode("exact");
      setReplayTargetUrl("");
      setReplayHeaders(JSON.stringify(selected.headers || {}, null, 2));
      setIsEditingPayload(false);
      setDiffResult(null);
      setSchemaResult(null);
    }
  }, [selected]);

  const handleClearHistory = () => {
    if (!clearConfirmRef.current) {
      clearConfirmRef.current = true;
      setClearConfirm(true);
      showToast({ tone: "info", message: "Click Clear history again to delete all webhook logs." });
      window.setTimeout(() => {
        clearConfirmRef.current = false;
        setClearConfirm(false);
      }, 5000);
      return;
    }
    clearConfirmRef.current = false;
    setClearConfirm(false);
    trackEvent("feature_used", { feature_name: "clear_webhook_history" });
    historyClearedRef.current = true;
    refreshGenerationRef.current += 1;
    setHasServerSearch(false);
    setRequests([]);
    setSelected(null);
    setSummary((current) => current ? {
      ...current,
      total_requests: 0,
      recent_24h: 0,
      retry_pressure: 0,
      failed_forwards: 0,
      auto_retry_enabled: 0,
    } : current);
    void apiClient.delete("/webhooks/requests?confirm=CONFIRM")
      .then(() => {
        showToast({ tone: "success", message: "Your connection history was cleared." });
        window.setTimeout(() => {
          historyClearedRef.current = false;
          void refreshWebhooks(false);
        }, 1500);
      })
      .catch(() => {
        historyClearedRef.current = false;
        void refreshWebhooks(false);
        showToast({ tone: "error", message: "We could not clear your history. Retry in a moment." });
      });
    window.setTimeout(() => {
      if (historyClearedRef.current) {
        historyClearedRef.current = false;
        void refreshWebhooks(false);
      }
    }, 15000);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(endpointUrl);
    setCopied(true);
    showToast({ tone: "success", message: "Your connection URL was copied." });
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCreateEndpoint = async () => {
    setCreatingEndpoint(true);
    trackEvent("feature_used", { feature_name: "webhook_create_endpoint" });
    try {
      const methods = endpointForm.methods.split(",").map(method => method.trim().toUpperCase()).filter(Boolean);
      const { data } = await apiClient.post<WebhookEndpoint>("/webhooks/endpoints", {
        name: endpointForm.name || "Production endpoint",
        methods,
      });
      setEndpoints(current => [data, ...current]);
      setEndpointForm({ name: "", methods: "POST" });
      showToast({ tone: "success", message: "Endpoint created. Copy its URL into your provider." });
    } catch (error: any) {
      showToast({ tone: "error", message: getSettingsErrorMessage(error, "Endpoint could not be created.") });
    } finally {
      setCreatingEndpoint(false);
    }
  };

  const handleSendTestWebhook = async () => {
    const targetUrl = endpoints[0]?.endpoint_url || endpointUrl;
    if (!targetUrl) {
      showToast({ tone: "info", message: "Create or copy a connection URL before sending a test webhook." });
      return;
    }

    trackEvent("feature_used", { feature_name: "webhook_send_test_event" });
    try {
      await fetch(targetUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-DevForge-Test": "true",
        },
        body: JSON.stringify({
          type: "payment_intent.succeeded",
          provider: "devforge_test",
          amount: 4200,
          currency: "usd",
          created_at: new Date().toISOString(),
        }),
      });
      showToast({ tone: "success", message: "Test webhook sent. It should appear in the delivery log shortly." });
      refreshWebhooks(false);
    } catch {
      showToast({ tone: "error", message: "We could not send the test webhook from this browser." });
    }
  };

  const handleDeleteEndpoint = async (endpoint: WebhookEndpoint) => {
    setDeletingEndpointId(endpoint.id);
    trackEvent("feature_used", { feature_name: "webhook_delete_endpoint" });
    try {
      await apiClient.delete(`/webhooks/endpoints/${endpoint.id}`);
      setEndpoints(current => current.filter(item => item.id !== endpoint.id));
      if (endpoint.endpoint_url === endpointUrl) setEndpointUrl("");
      showToast({ tone: "success", message: "Endpoint and its events were deleted." });
    } catch (error: any) {
      showToast({ tone: "error", message: getSettingsErrorMessage(error, "Endpoint could not be deleted.") });
    } finally {
      setDeletingEndpointId(null);
    }
  };

  const handleRetry = async () => {
    if (!selected) return;
    if (editedPayloadInvalid) {
      showToast({ tone: "error", message: "Payload must be valid JSON before retrying." });
      return;
    }
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
      showToast({ tone: "error", message: getSettingsErrorMessage(err, "We could not retry this delivery. Check the payload and try again.") });
    } finally {
      setIsRetrying(false);
    }
  };

  const handleServerSearch = async () => {
    setIsSearching(true);
    setHasServerSearch(true);
    trackEvent("feature_used", { feature_name: "webhook_search" });
    try {
      const { data } = await apiClient.post<{ total: number; items: WebhookRequest[] }>("/webhooks/search", {
        json_path: jsonSearchPath,
        equals: jsonSearchEquals || null,
        status: logStatus,
        method: methodFilter,
        provider: providerFilter,
        date_from: dateFrom || null,
        date_to: dateTo || null,
        query: search || "",
      });
      setRequests(data.items);
      setSelected(data.items[0] || null);
      showToast({ tone: "success", message: `Search returned ${data.total === 1 ? "1 delivery" : `${data.total} deliveries`}.` });
    } catch (err: any) {
      showToast({ tone: "error", message: getSettingsErrorMessage(err, "We could not search deliveries.") });
    } finally {
      setIsSearching(false);
    }
  };

  const clearServerSearch = () => {
    setSearch("");
    setJsonSearchPath("");
    setJsonSearchEquals("");
    setMethodFilter("");
    setProviderFilter("");
    setDateFrom("");
    setDateTo("");
    setLogStatus("all");
    setHasServerSearch(false);
  };

  const handleReplay = async () => {
    if (!selected) return;
    let headersOverride: Record<string, string> | null = null;
    if (replayMode !== "exact") {
      try {
        headersOverride = JSON.parse(replayHeaders || "{}");
      } catch {
        showToast({ tone: "error", message: "Replay headers must be valid JSON." });
        return;
      }
      if (retryPayload.trim()) {
        try {
          JSON.parse(retryPayload);
        } catch {
          showToast({ tone: "error", message: "Replay payload must be valid JSON." });
          return;
        }
      }
    }

    setIsReplaying(true);
    trackEvent("feature_used", { feature_name: "webhook_replay", mode: replayMode });
    try {
      const { data } = await apiClient.post<ReplayResponse>(`/webhooks/events/${selected.id}/replay`, {
        mode: replayMode,
        target_url: replayMode === "alternate" ? replayTargetUrl : "",
        body_override: replayMode === "exact" ? null : retryPayload,
        headers_override: headersOverride,
      });
      showToast({
        tone: data.status === "success" ? "success" : "error",
        message: data.status === "success" ? "Replay sent successfully." : data.error || "Replay failed.",
      });
      refreshWebhooks(false);
    } catch (err: any) {
      showToast({ tone: "error", message: getSettingsErrorMessage(err, "We could not replay this delivery.") });
    } finally {
      setIsReplaying(false);
    }
  };

  const selectedIndex = selected ? requests.findIndex(req => req.id === selected.id) : -1;
  const previousRequest = selectedIndex >= 0 ? requests[selectedIndex + 1] : null;
  const endpointLimitLabel = `${endpoints.length}/${endpointLimit} ${endpointPlan.charAt(0).toUpperCase()}${endpointPlan.slice(1)}`;

  const handleCompareWithPrevious = async () => {
    if (!selected || !previousRequest) return;
    setIsDiffing(true);
    trackEvent("feature_used", { feature_name: "webhook_diff" });
    try {
      const { data } = await apiClient.get<RequestDiff>(
        `/webhooks/requests/${selected.id}/diff?base_request_id=${previousRequest.id}`
      );
      setDiffResult(data);
      showToast({ tone: "success", message: "Delivery diff generated." });
    } catch (err: any) {
      showToast({ tone: "error", message: getSettingsErrorMessage(err, "We could not compare these deliveries.") });
    } finally {
      setIsDiffing(false);
    }
  };

  const handleValidateSchema = async () => {
    if (!selected) return;
    let schema: unknown;
    try {
      schema = JSON.parse(schemaText);
    } catch {
      showToast({ tone: "error", message: "Schema must be valid JSON." });
      return;
    }

    setIsValidatingSchema(true);
    trackEvent("feature_used", { feature_name: "webhook_schema_validation" });
    try {
      const { data } = await apiClient.post<SchemaValidationResult>(
        `/webhooks/requests/${selected.id}/validate-schema`,
        { schema }
      );
      setSchemaResult(data);
      showToast({
        tone: data.valid ? "success" : "info",
        message: data.valid ? "Payload matches the schema." : "Schema validation found payload drift.",
      });
    } catch (err: any) {
      showToast({ tone: "error", message: getSettingsErrorMessage(err, "We could not validate this payload.") });
    } finally {
      setIsValidatingSchema(false);
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

  const handleEventExport = async (format: EventExportFormat) => {
    if (!selected) return;

    setEventExporting(format);
    trackEvent("feature_used", { feature_name: "export_webhook_event", format });
    try {
      const filename =
        format === "curl"
          ? `webhook-request-${selected.id}.curl.sh`
          : format === "postman"
          ? `webhook-request-${selected.id}.postman_collection.json`
          : format === "har"
          ? `webhook-request-${selected.id}.har`
          : `webhook-request-${selected.id}.openapi.json`;
      await downloadFile(`/webhooks/requests/${selected.id}${eventExportQueries[format]}`, filename);
      showToast({
        tone: "success",
        message:
          format === "curl"
            ? "cURL export downloaded."
            : format === "postman"
            ? "Postman collection downloaded."
            : format === "har"
            ? "HAR export downloaded."
            : "OpenAPI spec downloaded.",
      });
    } catch {
      showToast({ tone: "error", message: "We could not export this delivery. Retry from the inspector." });
    } finally {
      setEventExporting(null);
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
  const hasActiveSearch = hasServerSearch || Boolean(
    search.trim() || jsonSearchPath.trim() || jsonSearchEquals.trim() || methodFilter || providerFilter || dateFrom || dateTo || logStatus !== "all"
  );

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  const formatDiffValue = (value: unknown) => {
    if (typeof value === "string") return value;
    if (value === undefined) return "";
    return JSON.stringify(value);
  };

  const renderDiffRows = (items: DiffItem[], tone: "added" | "removed" | "changed") => {
    const colors = {
      added: "text-emerald-400",
      removed: "text-red-400",
      changed: "text-amber-400",
    };
    return items.slice(0, 6).map(item => (
      <div key={`${tone}-${item.path}-${formatDiffValue(item.value ?? item.new_value ?? item.old_value)}`} className="rounded-md bg-black/20 p-2">
        <div className={`font-mono text-[10px] ${colors[tone]}`}>{item.path}</div>
        {tone === "changed" ? (
          <div className="mt-1 grid grid-cols-2 gap-2 text-[10px] opacity-80">
            <span className="break-all">Old: {formatDiffValue(item.old_value)}</span>
            <span className="break-all">New: {formatDiffValue(item.new_value)}</span>
          </div>
        ) : (
          <div className="mt-1 break-all text-[10px] opacity-80">
            {formatDiffValue(tone === "added" ? item.value : item.old_value)}
          </div>
        )}
      </div>
    ));
  };

  return (
    <div className="dashboard-motion flex flex-col h-full max-w-[1600px] mx-auto overflow-hidden">
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
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          {/* Export Dropdown */}
          <div className="relative" ref={exportRef}>
            <button
              onClick={() => setExportOpen(!exportOpen)}
              className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all"
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
            className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-all"
          >
            <Trash2 size={16} />
            <span>{clearConfirm ? "Confirm clear" : "Clear history"}</span>
          </button>
        </div>
      </div>

      <div className="mb-6 px-4">
        <DashboardPlanPanel
          product={dashboardProduct}
          quotas={[
            { label: "Events today", used: summary?.recent_24h ?? requests.length },
            { label: "Endpoints", used: endpoints.length },
            { label: "Retention", used: 0 },
          ]}
        />
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 px-4 xl:grid-cols-[1fr_360px]">
        <section className="rounded-xl p-4" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
          <div className="mb-3 flex items-center justify-between gap-4">
            <div>
              <h2 className="text-sm font-bold" style={{ color: "var(--color-text)" }}>Endpoints</h2>
              <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>
                Create provider-specific webhook URLs, choose allowed methods, and inspect events per endpoint.
              </p>
            </div>
            <span className="rounded px-2 py-1 font-mono text-xs text-[var(--color-accent)] bg-black/10">
              {endpointLimitLabel}
            </span>
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            {endpoints.map(endpoint => (
              <div key={endpoint.id} className="rounded-lg p-3" style={{ backgroundColor: "var(--color-surface-high)" }}>
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold" style={{ color: "var(--color-text)" }}>{endpoint.name}</p>
                    <p className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>
                      {endpoint.methods.join(", ")} · {endpoint.is_active ? "active" : "inactive"}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteEndpoint(endpoint)}
                    disabled={deletingEndpointId === endpoint.id}
                    className="rounded-md px-2 py-1 text-[10px] font-bold text-red-500 transition-colors hover:bg-red-500/10 disabled:opacity-60"
                  >
                    {deletingEndpointId === endpoint.id ? "Deleting" : "Delete"}
                  </button>
                </div>
                <div className="flex items-center gap-2 rounded bg-black/10 p-2">
                  <code className="min-w-0 flex-1 truncate text-[11px]" style={{ color: "var(--color-text)" }}>{endpoint.endpoint_url}</code>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(endpoint.endpoint_url);
                      showToast({ tone: "success", message: "Endpoint URL copied." });
                    }}
                    className="rounded px-2 py-1 text-[10px] font-bold text-[var(--color-accent)] hover:bg-black/10"
                  >
                    Copy
                  </button>
                </div>
              </div>
            ))}
            {endpoints.length === 0 ? (
              <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>No endpoints yet. Creating config will provision the default endpoint automatically.</p>
            ) : null}
          </div>
        </section>

        <section className="rounded-xl p-4" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
          <h2 className="text-sm font-bold" style={{ color: "var(--color-text)" }}>New endpoint</h2>
          <p className="mb-3 text-xs" style={{ color: "var(--color-text-secondary)" }}>Use a descriptive name per provider or environment.</p>
          <div className="space-y-2">
            <input
              value={endpointForm.name}
              onChange={event => setEndpointForm(current => ({ ...current, name: event.target.value }))}
              className="input-field w-full text-xs"
              placeholder="Stripe production"
            />
            <input
              value={endpointForm.methods}
              onChange={event => setEndpointForm(current => ({ ...current, methods: event.target.value }))}
              className="input-field w-full text-xs font-mono"
              placeholder="POST, PUT"
            />
            <button
              type="button"
              onClick={handleCreateEndpoint}
              disabled={creatingEndpoint}
              className="btn-primary w-full justify-center text-xs"
            >
              {creatingEndpoint ? <InlineSpinner /> : null}
              Create endpoint
            </button>
          </div>
        </section>
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

      {!loading && !loadError && requests.length === 0 && !hasActiveSearch && (
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
          <div className="mt-3 flex justify-center">
            <button
              type="button"
              onClick={handleSendTestWebhook}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <Send size={14} />
              Send test webhook
            </button>
          </div>
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
              {stat.label === "Failed forwards" ? (
                <p className="mt-1 text-[10px] leading-snug opacity-60">
                  Failed forwards are delivery attempts that reached Webhook Monitor but did not succeed at your target endpoint; retries are resend attempts.
                </p>
              ) : null}
              {stat.label === "Auto retry" ? (
                <p className="mt-1 text-[10px] leading-snug opacity-60">
                  Auto retry is visible here so delivery automation is never hidden in the log filters.
                </p>
              ) : null}
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

          <div className="mb-4 grid gap-3 rounded-lg p-3 md:grid-cols-6" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <label className="md:col-span-2 text-[10px] font-bold uppercase tracking-wider opacity-70">
              Search JSON path
              <input
                type="text"
                value={jsonSearchPath}
                onChange={event => setJsonSearchPath(event.target.value)}
                className="input-field mt-1 w-full text-xs normal-case"
                placeholder="type"
              />
            </label>
            <label className="md:col-span-2 text-[10px] font-bold uppercase tracking-wider opacity-70">
              JSON equals
              <input
                type="text"
                value={jsonSearchEquals}
                onChange={event => setJsonSearchEquals(event.target.value)}
                className="input-field mt-1 w-full text-xs normal-case"
                placeholder="payment_intent.succeeded"
              />
            </label>
            <label className="text-[10px] font-bold uppercase tracking-wider opacity-70">
              Method filter
              <select value={methodFilter} onChange={event => setMethodFilter(event.target.value)} className="input-field mt-1 w-full text-xs normal-case">
                <option value="">Any</option>
                {["POST", "PUT", "PATCH", "DELETE", "GET"].map(method => <option key={method} value={method}>{method}</option>)}
              </select>
            </label>
            <label className="text-[10px] font-bold uppercase tracking-wider opacity-70">
              Provider filter
              <select value={providerFilter} onChange={event => setProviderFilter(event.target.value)} className="input-field mt-1 w-full text-xs normal-case">
                <option value="">Any</option>
                {["stripe", "github", "shopify", "generic"].map(provider => <option key={provider} value={provider}>{provider}</option>)}
              </select>
            </label>
            <label className="md:col-span-2 text-[10px] font-bold uppercase tracking-wider opacity-70">
              Date from
              <input
                type="datetime-local"
                value={dateFrom}
                onChange={event => setDateFrom(event.target.value)}
                className="input-field mt-1 w-full text-xs normal-case"
              />
            </label>
            <label className="md:col-span-2 text-[10px] font-bold uppercase tracking-wider opacity-70">
              Date to
              <input
                type="datetime-local"
                value={dateTo}
                onChange={event => setDateTo(event.target.value)}
                className="input-field mt-1 w-full text-xs normal-case"
              />
            </label>
            <button
              type="button"
              onClick={handleServerSearch}
              disabled={isSearching}
              className="md:col-span-2 rounded-lg bg-[var(--color-primary)] px-3 py-2 text-xs font-bold text-black transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSearching ? "Searching..." : "Run search"}
            </button>
            {hasActiveSearch ? (
              <button type="button" onClick={clearServerSearch} className="md:col-span-2 rounded-lg px-3 py-2 text-xs font-bold" style={{ backgroundColor: "var(--color-surface-high)", color: "var(--color-text-secondary)" }}>
                Clear search
              </button>
            ) : null}
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
                  {hasActiveSearch ? "No deliveries match your search filters" : "Waiting for your first webhook..."}
                </p>
              </div>
            ) : (
              <>
              <div className="md:hidden divide-y divide-[var(--color-border)]/50">
                {filtered.map(req => (
                  <button
                    key={req.id}
                    type="button"
                    onClick={() => setSelected(req)}
                    className="w-full p-4 text-left transition-all hover:bg-black/5"
                    style={{
                      backgroundColor: selected?.id === req.id ? "rgba(var(--color-primary-rgb), 0.05)" : "transparent",
                    }}
                  >
                    <div className="flex items-center justify-between gap-3 mb-3">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded border"
                          style={{
                            backgroundColor: `${methodColors[req.method] || "#A3A3A3"}15`,
                            color: methodColors[req.method] || "#A3A3A3",
                            borderColor: `${methodColors[req.method] || "#A3A3A3"}30`
                          }}>
                          {req.method}
                        </span>
                        <span className="text-xs font-mono truncate" style={{ color: "var(--color-text)" }}>
                          {req.path}
                        </span>
                      </div>
                      <ChevronRight size={16} className={`flex-shrink-0 transition-transform ${selected?.id === req.id ? "rotate-90 text-[var(--color-primary)]" : "opacity-30"}`} />
                    </div>
                    <div className="flex items-center justify-between gap-3 text-[11px] font-mono" style={{ color: "var(--color-text-secondary)" }}>
                      <span>{formatTime(req.received_at)}</span>
                      <span>
                        {req.retry_count > 0 ? `${req.retry_count} retries` : "No retries"}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
              <div className="dashboard-table-scroll hidden md:block">
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
              </div>
              </>
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
                <h3 className="text-[10px] font-bold uppercase tracking-widest mb-3 opacity-50">Signature</h3>
                <div className="rounded-lg bg-black/20 p-4 text-xs">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-mono opacity-60">{selected.signature_provider || "not configured"}</span>
                    <span
                      className="rounded px-2 py-0.5 text-[10px] font-bold uppercase"
                      style={{
                        backgroundColor:
                          selected.signature_valid === true
                            ? "rgba(16,185,129,0.12)"
                            : selected.signature_valid === false
                              ? "rgba(239,68,68,0.12)"
                              : "rgba(148,163,184,0.12)",
                        color:
                          selected.signature_valid === true
                            ? "#10B981"
                            : selected.signature_valid === false
                              ? "#EF4444"
                              : "var(--color-text-secondary)",
                      }}
                    >
                      {selected.signature_valid === true ? "valid" : selected.signature_valid === false ? "invalid" : "not checked"}
                    </span>
                  </div>
                  {selected.signature_error ? (
                    <p className="mt-2 break-all font-mono text-[10px] text-red-400">{selected.signature_error}</p>
                  ) : null}
                  <div className="mt-3 grid grid-cols-2 gap-2 font-mono text-[10px] opacity-70">
                    <span>IP: {selected.ip_address || "unknown"}</span>
                    <span>Event: {selected.event_id || selected.id}</span>
                  </div>
                </div>
              </section>

              <section>
                <h3 className="text-[10px] font-bold uppercase tracking-widest mb-3 opacity-50">Schema Ingestion Validation</h3>
                <div className="rounded-lg bg-black/20 p-4 text-xs">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-mono opacity-60">Schema match</span>
                    <span
                      className="rounded px-2 py-0.5 text-[10px] font-bold uppercase"
                      style={{
                        backgroundColor:
                          selected.schema_valid === true
                            ? "rgba(16,185,129,0.12)"
                            : selected.schema_valid === false
                              ? "rgba(239,68,68,0.12)"
                              : "rgba(148,163,184,0.12)",
                        color:
                          selected.schema_valid === true
                            ? "#10B981"
                            : selected.schema_valid === false
                              ? "#EF4444"
                              : "var(--color-text-secondary)",
                      }}
                    >
                      {selected.schema_valid === true ? "valid" : selected.schema_valid === false ? "invalid" : "unchecked"}
                    </span>
                  </div>
                  {selected.schema_error ? (
                    <p className="mt-2 break-all font-mono text-[10px] text-red-400">{selected.schema_error}</p>
                  ) : null}
                </div>
              </section>

              <section>
                <h3 className="text-[10px] font-bold uppercase tracking-widest mb-3 opacity-50">Event Export</h3>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    aria-label="Export cURL"
                    onClick={() => handleEventExport("curl")}
                    disabled={eventExporting !== null}
                    className="rounded-lg bg-black/10 px-3 py-2 text-left text-xs font-bold transition-colors hover:bg-black/20 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {eventExporting === "curl" ? "Exporting..." : "Copy as cURL"}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleEventExport("postman")}
                    disabled={eventExporting !== null}
                    className="rounded-lg bg-black/10 px-3 py-2 text-left text-xs font-bold transition-colors hover:bg-black/20 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {eventExporting === "postman" ? "Exporting..." : "Export Postman"}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleEventExport("har")}
                    disabled={eventExporting !== null}
                    className="rounded-lg bg-black/10 px-3 py-2 text-left text-xs font-bold transition-colors hover:bg-black/20 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {eventExporting === "har" ? "Exporting..." : "Export HAR"}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleEventExport("openapi")}
                    disabled={eventExporting !== null}
                    className="rounded-lg bg-black/10 px-3 py-2 text-left text-xs font-bold transition-colors hover:bg-black/20 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {eventExporting === "openapi" ? "Exporting..." : "Export OpenAPI"}
                  </button>
                </div>
              </section>

              <section>
                <h3 className="text-[10px] font-bold uppercase tracking-widest mb-3 opacity-50">Diff and Schema</h3>
                <div className="space-y-4">
                  <div>
                    <button
                      type="button"
                      onClick={handleCompareWithPrevious}
                      disabled={!previousRequest || isDiffing}
                      className="w-full rounded-lg bg-black/10 px-3 py-2 text-left text-xs font-bold transition-colors hover:bg-black/20 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isDiffing ? "Comparing..." : "Compare with previous"}
                    </button>
                    {!previousRequest ? (
                      <p className="mt-1.5 text-[10px] opacity-50">Select a newer delivery with an older neighbor to generate a diff.</p>
                    ) : null}
                  </div>

                  {diffResult ? (
                    <div className="space-y-3 rounded-lg bg-black/10 p-3">
                      <div className="grid grid-cols-3 gap-2 text-center text-[10px] font-bold uppercase tracking-wider">
                        <span className="text-emerald-400">{diffResult.body.added.length + diffResult.headers.added.length} added</span>
                        <span className="text-red-400">{diffResult.body.removed.length + diffResult.headers.removed.length} removed</span>
                        <span className="text-amber-400">{diffResult.body.changed.length + diffResult.headers.changed.length} changed</span>
                      </div>
                      <div className="space-y-2">
                        {renderDiffRows(diffResult.body.added, "added")}
                        {renderDiffRows(diffResult.body.removed, "removed")}
                        {renderDiffRows(diffResult.body.changed, "changed")}
                        {renderDiffRows(diffResult.headers.changed, "changed")}
                      </div>
                    </div>
                  ) : null}

                  <div className="space-y-2">
                    <textarea
                      value={schemaText}
                      onChange={event => setSchemaText(event.target.value)}
                      className="min-h-[120px] w-full resize-y rounded-lg border border-black/10 bg-black/20 p-3 font-mono text-[11px] text-emerald-400/90 outline-none focus:border-[var(--color-primary)]"
                      spellCheck={false}
                    />
                    <button
                      type="button"
                      onClick={handleValidateSchema}
                      disabled={isValidatingSchema}
                      className="w-full rounded-lg bg-[var(--color-primary)] px-3 py-2 text-xs font-bold text-black transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isValidatingSchema ? "Validating..." : "Validate Schema"}
                    </button>
                  </div>

                  {schemaResult ? (
                    <div
                      className="rounded-lg p-3 text-xs"
                      style={{
                        backgroundColor: schemaResult.valid ? "rgba(16,185,129,0.08)" : "rgba(245,158,11,0.08)",
                        border: schemaResult.valid ? "1px solid rgba(16,185,129,0.2)" : "1px solid rgba(245,158,11,0.2)",
                      }}
                    >
                      <p className="font-bold" style={{ color: schemaResult.valid ? "#10B981" : "#F59E0B" }}>
                        {schemaResult.valid ? "Schema matched" : `${schemaResult.errors.length} schema issue${schemaResult.errors.length === 1 ? "" : "s"}`}
                      </p>
                      {!schemaResult.valid ? (
                        <div className="mt-2 space-y-1 font-mono text-[10px]">
                          {schemaResult.errors.slice(0, 5).map(error => (
                            <p key={`${error.path}-${error.message}`} className="break-words">
                              <span className="text-amber-400">{error.path}</span>: {error.message}
                            </p>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </section>

              <section>
                <h3 className="text-[10px] font-bold uppercase tracking-widest mb-3 opacity-50">Replay</h3>
                <div className="space-y-3">
                  <div className="grid grid-cols-3 gap-2">
                    {([
                      ["exact", "Replay exact"],
                      ["modified", "Replay modified"],
                      ["alternate", "Replay alternate"],
                    ] as [ReplayMode, string][]).map(([mode, label]) => (
                      <button
                        key={mode}
                        type="button"
                        onClick={() => setReplayMode(mode)}
                        className="rounded-lg px-2 py-2 text-[10px] font-bold transition-colors"
                        style={{
                          backgroundColor: replayMode === mode ? "var(--color-accent-dim)" : "rgba(0,0,0,0.12)",
                          color: replayMode === mode ? "var(--color-accent)" : "var(--color-text-secondary)",
                        }}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  {replayMode === "alternate" ? (
                    <label className="block text-[10px] font-bold uppercase tracking-wider opacity-70">
                      Replay target URL
                      <input
                        type="url"
                        value={replayTargetUrl}
                        onChange={event => setReplayTargetUrl(event.target.value)}
                        className="input-field mt-1 w-full text-xs normal-case"
                        placeholder="https://localhost-tunnel.example/webhook"
                      />
                    </label>
                  ) : null}
                  {replayMode !== "exact" ? (
                    <label className="block text-[10px] font-bold uppercase tracking-wider opacity-70">
                      Replay headers JSON
                      <textarea
                        value={replayHeaders}
                        onChange={event => setReplayHeaders(event.target.value)}
                        className="mt-1 min-h-[90px] w-full resize-y rounded-lg border border-black/10 bg-black/20 p-3 font-mono text-[11px] text-emerald-400/90 outline-none focus:border-[var(--color-primary)]"
                        spellCheck={false}
                      />
                    </label>
                  ) : null}
                  <button
                    type="button"
                    onClick={handleReplay}
                    disabled={isReplaying}
                    className="w-full rounded-lg bg-black/10 px-3 py-2 text-left text-xs font-bold transition-colors hover:bg-black/20 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isReplaying ? "Replaying..." : "Send replay"}
                  </button>
                </div>
              </section>

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
                      <span>{editedPayloadInvalid ? "Payload must be valid JSON before retrying." : "You are about to retry this delivery with an edited payload."}</span>
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
                disabled={isRetrying || editedPayloadInvalid}
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
