"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Clock,
  Download,
  FileText,
  History,
  Pause,
  Play,
  Plus,
  Upload,
} from "lucide-react";

const dashboardProduct = getProduct("invoicefollow");

type InvoiceStatus = "pending" | "paid" | "overdue" | "paused" | "in_sequence" | "finalized";

interface Invoice {
  id: number;
  client_name: string;
  client_email: string;
  amount: number;
  currency: string;
  due_date: string;
  issued_date?: string | null;
  invoice_number?: string;
  source?: string;
  status: InvoiceStatus;
  reminders_sent: number;
  cron_paused?: boolean;
  schedule_paused_until?: string | null;
  manual_review_reason?: string;
  notes?: string;
}

interface MetricSummary {
  total_invoices: number;
  recovered_count: number;
  pending_count: number;
  recovery_rate: number;
  recovered_amount: number;
  pending_amount: number;
  avg_payment_time_days: number;
  at_risk_count: number;
}

interface DigestSummary {
  payments_detected_this_week: number;
  valid_excuses_pending: number;
  reminders_sent: number;
  invoices_at_risk: number;
  month_summary: {
    recovered_amount: number;
    pending_amount: number;
    recovery_rate: number;
  };
}

interface ClientScore {
  client_email: string;
  client_name: string;
  total_invoices: number;
  paid: number;
  overdue: number;
  avg_reminders: number;
  risk_score: number;
  risk_label: "alto" | "medio" | "bajo";
}

interface InvoiceSettingsSummary {
  forward_address: string;
  connections: Record<"gmail" | "outlook" | "stripe" | "paypal", boolean>;
}

interface DetectedInvoiceDraft {
  status: string;
  draft_id?: number;
  requires_user_confirmation?: boolean;
  client_name?: string;
  client_email?: string;
  amount?: number;
  currency?: string;
  due_date?: string;
  issued_date?: string | null;
  invoice_number?: string;
  confidence?: number;
  reason?: string;
}

interface TimelineResponse {
  timeline: Array<{ day: number; name: string; tone: string; sender_label: string; status: string }>;
  emails_sent: Array<{ id?: number; subject: string; status: string; sent_at: string; body_preview?: string }>;
  client_replies: Array<{ id?: number; text: string; intent_label: string; action_taken: string; received_at: string }>;
  payments_detected: Array<{ id?: number; provider: string; amount: number; currency: string; status: string; detected_at: string }>;
  notes?: string;
}

const statusStyles: Record<string, { backgroundColor: string; color: string }> = {
  pending: { backgroundColor: "rgba(245,158,11,0.15)", color: "#B45309" },
  overdue: { backgroundColor: "rgba(239,68,68,0.13)", color: "#DC2626" },
  paused: { backgroundColor: "rgba(99,102,241,0.13)", color: "#4F46E5" },
  in_sequence: { backgroundColor: "rgba(14,165,233,0.13)", color: "#0284C7" },
  finalized: { backgroundColor: "rgba(115,115,115,0.14)", color: "#525252" },
  paid: { backgroundColor: "rgba(16,185,129,0.14)", color: "#059669" },
};

function money(amount: number, currency: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currency || "USD" }).format(amount || 0);
}

function daysOverdue(dueDate: string) {
  const due = new Date(`${dueDate}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.max(0, Math.floor((today.getTime() - due.getTime()) / 86400000));
}

function nextStep(invoice: Invoice) {
  if (invoice.status === "paid") return "Paid";
  if (invoice.cron_paused || invoice.status === "paused") return invoice.schedule_paused_until ? `Paused until ${invoice.schedule_paused_until}` : "Paused";
  const late = daysOverdue(invoice.due_date);
  if (late >= 45) return "Manual action";
  if (late >= 30) return "Final Notice";
  if (late >= 15) return "Second Reminder";
  if (late >= 7) return "First Reminder";
  return "Invoice Original";
}

export default function DashboardPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [metrics, setMetrics] = useState<MetricSummary | null>(null);
  const [digest, setDigest] = useState<DigestSummary | null>(null);
  const [clientScores, setClientScores] = useState<ClientScore[]>([]);
  const [settings, setSettings] = useState<InvoiceSettingsSummary | null>(null);
  const [emailDraftInput, setEmailDraftInput] = useState({
    subject: "",
    body: "",
    sender_email: "",
    sender_name: "",
  });
  const [detectedDraft, setDetectedDraft] = useState<DetectedInvoiceDraft | null>(null);
  const [detectingEmail, setDetectingEmail] = useState(false);
  const [confirmingDraft, setConfirmingDraft] = useState(false);
  const [selected, setSelected] = useState<Invoice | null>(null);
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [loadingIds, setLoadingIds] = useState<Set<number>>(new Set());
  const [showForm, setShowForm] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [toast, setToast] = useState<DashboardToast | null>(null);
  const [form, setForm] = useState({
    client_name: "",
    client_email: "",
    amount: "",
    currency: "USD",
    due_date: "",
    issued_date: "",
    invoice_number: "",
    notes: "",
  });
  const exportRef = useRef<HTMLDivElement>(null);

  const showToast = useCallback((nextToast: DashboardToast) => {
    setToast(nextToast);
    window.setTimeout(() => setToast(null), 4500);
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    const [invoiceResult, metricResult, digestResult, scoreResult, settingsResult] = await Promise.allSettled([
      apiClient.get<Invoice[]>("/invoices"),
      apiClient.get<MetricSummary>("/metrics"),
      apiClient.get<DigestSummary>("/digest"),
      apiClient.get<ClientScore[]>("/invoices/client-scores"),
      apiClient.get<InvoiceSettingsSummary>("/settings"),
    ]);
    if (invoiceResult.status === "fulfilled") setInvoices(invoiceResult.value.data);
    if (metricResult.status === "fulfilled") setMetrics(metricResult.value.data);
    if (digestResult.status === "fulfilled") setDigest(digestResult.value.data);
    if (scoreResult.status === "fulfilled") setClientScores(scoreResult.value.data);
    if (settingsResult.status === "fulfilled") setSettings(settingsResult.value.data);
    if (
      invoiceResult.status === "rejected" &&
      metricResult.status === "rejected" &&
      digestResult.status === "rejected" &&
      scoreResult.status === "rejected" &&
      settingsResult.status === "rejected"
    ) {
      setLoadError(true);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(event.target as Node)) setExportOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const totals = useMemo(() => {
    const pendingAmount = invoices.filter((invoice) => invoice.status !== "paid").reduce((sum, invoice) => sum + invoice.amount, 0);
    const atRisk = invoices.filter((invoice) => invoice.status !== "paid" && daysOverdue(invoice.due_date) > 30).length;
    return { pendingAmount, atRisk };
  }, [invoices]);

  const saveRecord = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    trackEvent("feature_used", { feature_name: "invoicefollow_manual_tracking_record" });
    try {
      const { data } = await apiClient.post<Invoice>("/invoices", {
        ...form,
        amount: Number(form.amount),
        issued_date: form.issued_date || null,
      });
      setInvoices((current) => [data, ...current]);
      setForm({ client_name: "", client_email: "", amount: "", currency: "USD", due_date: "", issued_date: "", invoice_number: "", notes: "" });
      setShowForm(false);
      showToast({ tone: "success", message: "Existing invoice record is now tracked." });
      refresh();
    } catch (error: any) {
      showToast({ tone: "error", message: error.detail || "We could not save this tracking record." });
    } finally {
      setSaving(false);
    }
  };

  const importExistingRecords = async (fileInput: File) => {
    setImporting(true);
    trackEvent("feature_used", { feature_name: "invoicefollow_import_existing_records", format: fileInput.name.split(".").pop() });
    try {
      const formData = new FormData();
      formData.append("file", fileInput);
      const { data } = await uploadFile<{ created: number; invoices: Invoice[] }>("/invoices/import-csv", formData);
      setInvoices((current) => [...data.invoices, ...current]);
      showToast({ tone: "success", message: `${data.created} existing invoice records imported.` });
      refresh();
    } catch (error: any) {
      showToast({ tone: "error", message: error.detail || "Import failed. Use CSV/XLS/XLSX with client, email, amount, and due date." });
    } finally {
      setImporting(false);
    }
  };

  const openImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".csv,.xlsx,.xls";
    input.onchange = (event) => {
      const file = (event.target as HTMLInputElement).files?.[0];
      if (file) importExistingRecords(file);
    };
    input.click();
  };

  const mutateInvoice = async (id: number, action: "pause" | "resume" | "mark-paid") => {
    setLoadingIds((current) => new Set(current).add(id));
    trackEvent("feature_used", { feature_name: `invoicefollow_${action}` });
    try {
      await apiClient.post(`/invoices/${id}/${action}`);
      showToast({ tone: "success", message: action === "mark-paid" ? "Payment marked." : action === "pause" ? "Sequence paused." : "Sequence resumed." });
      refresh();
    } catch {
      showToast({ tone: "error", message: "Action failed. Retry from the row." });
    } finally {
      setLoadingIds((current) => {
        const next = new Set(current);
        next.delete(id);
        return next;
      });
    }
  };

  const openTimeline = async (invoice: Invoice) => {
    setSelected(invoice);
    setTimeline(null);
    try {
      const { data } = await apiClient.get<TimelineResponse>(`/invoices/${invoice.id}/timeline`);
      setTimeline(data);
    } catch {
      showToast({ tone: "error", message: "Timeline could not be loaded." });
    }
  };

  const exportRecords = async (format: "csv" | "xlsx" | "json") => {
    setExportOpen(false);
    try {
      await downloadFile(`/invoices/export?format=${format}`, `invoicefollow_export.${format}`);
      showToast({ tone: "success", message: `Export started as ${format.toUpperCase()}.` });
    } catch {
      showToast({ tone: "error", message: "Export failed." });
    }
  };

  const detectInvoiceEmail = async () => {
    setDetectingEmail(true);
    setDetectedDraft(null);
    trackEvent("feature_used", { feature_name: "invoicefollow_detect_email" });
    try {
      const { data } = await apiClient.post<DetectedInvoiceDraft>("/invoices/detect-email", {
        ...emailDraftInput,
        source: "forward",
      });
      setDetectedDraft(data);
      showToast({
        tone: data.status === "detected" ? "success" : "info",
        message: data.status === "detected" ? "Invoice draft detected. Review before confirming." : data.reason || "No invoice details detected.",
      });
    } catch (error: any) {
      showToast({ tone: "error", message: error.response?.data?.detail || "Email detection failed." });
    } finally {
      setDetectingEmail(false);
    }
  };

  const confirmDetectedDraft = async () => {
    if (!detectedDraft?.draft_id || !detectedDraft.due_date) return;
    setConfirmingDraft(true);
    trackEvent("feature_used", { feature_name: "invoicefollow_confirm_detected_draft" });
    try {
      const { data } = await apiClient.post<{ invoice: Invoice }>(`/invoices/drafts/${detectedDraft.draft_id}/confirm`, {
        client_name: detectedDraft.client_name,
        client_email: detectedDraft.client_email,
        amount: detectedDraft.amount,
        currency: detectedDraft.currency,
        due_date: detectedDraft.due_date,
        issued_date: detectedDraft.issued_date || null,
        invoice_number: detectedDraft.invoice_number,
        notes: "Detected from pasted email in dashboard.",
      });
      setInvoices((current) => [data.invoice, ...current]);
      setDetectedDraft(null);
      showToast({ tone: "success", message: "Detected invoice is now tracked." });
      refresh();
    } catch (error: any) {
      showToast({ tone: "error", message: error.response?.data?.detail || "Could not confirm detected invoice." });
    } finally {
      setConfirmingDraft(false);
    }
  };

  return (
    <>
      <ActionToast toast={toast} onDismiss={() => setToast(null)} />
      <div className="dashboard-motion space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: "var(--color-text)" }}>Invoice recovery</h1>
            <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
              {invoices.length} tracked invoices · {money(metrics?.pending_amount ?? totals.pendingAmount, "USD")} pending
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative" ref={exportRef}>
              <button type="button" onClick={() => setExportOpen((value) => !value)} className="btn-secondary flex items-center gap-2">
                <Download size={14} />
                Export
                <ChevronDown size={14} />
              </button>
              {exportOpen ? (
                <div className="absolute right-0 top-full z-40 mt-2 w-40 overflow-hidden rounded-lg shadow-xl" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                  {(["csv", "xlsx", "json"] as const).map((format) => (
                    <button key={format} type="button" onClick={() => exportRecords(format)} className="block w-full px-4 py-2 text-left text-sm hover:bg-black/5" style={{ color: "var(--color-text)" }}>
                      {format.toUpperCase()}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
            <button type="button" onClick={openImport} disabled={importing} className="btn-secondary flex items-center gap-2">
              {importing ? <InlineSpinner /> : <Upload size={14} />}
              Import existing invoice records
            </button>
            <button type="button" onClick={() => setShowForm((value) => !value)} className="btn-primary flex items-center gap-2">
              <Plus size={14} />
              Add existing invoice record
            </button>
          </div>
        </div>

        <DashboardPlanPanel
          product={dashboardProduct}
          quotas={[
            { label: "Active invoices", used: invoices.filter((invoice) => invoice.status !== "paid").length, limit: 5, caption: "Free active invoice quota." },
            { label: "Emails this month", used: digest?.reminders_sent ?? 0, limit: 25, caption: "Free monthly reminder quota." },
            { label: "NLP reply analyses", used: digest?.valid_excuses_pending ?? 0, limit: 10, caption: "Free reply classification quota." },
          ]}
        />

        {loadError ? (
          <InlineErrorState
            title="InvoiceFollow could not load"
            description="The recovery dashboard did not load. Retry now, and contact support if it keeps happening."
            onRetry={refresh}
          />
        ) : null}

        {loading && invoices.length === 0 ? <DashboardSkeleton rows={4} metrics={4} /> : null}

        {!loading && !loadError && invoices.length === 0 ? (
          <WelcomeSteps
            title="Track your first existing invoice"
            description="Import records, connect Gmail or Outlook, or add a tracking record for an invoice already sent elsewhere."
            steps={[
              "Connect Gmail/Outlook or import existing invoice records.",
              "Confirm detected client, amount, currency, number, and due date.",
              "Let InvoiceFollow run reminders, classify replies, and reconcile payments.",
            ]}
            actionLabel="Add existing invoice record"
            onAction={() => setShowForm(true)}
          />
        ) : null}

        {showForm ? (
          <form onSubmit={saveRecord} className="grid grid-cols-1 gap-3 rounded-lg p-4 md:grid-cols-4" style={{ backgroundColor: "var(--color-surface)" }}>
            <input className="input-field" placeholder="Client" value={form.client_name} onChange={(event) => setForm({ ...form, client_name: event.target.value })} required />
            <input className="input-field" type="email" placeholder="Client email" value={form.client_email} onChange={(event) => setForm({ ...form, client_email: event.target.value })} required />
            <input className="input-field" placeholder="Invoice number" value={form.invoice_number} onChange={(event) => setForm({ ...form, invoice_number: event.target.value })} />
            <div className="grid grid-cols-[1fr_88px] gap-2">
              <input className="input-field" type="number" step="0.01" min="0.01" placeholder="Amount" value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} required />
              <input className="input-field" placeholder="USD" value={form.currency} onChange={(event) => setForm({ ...form, currency: event.target.value.toUpperCase() })} required />
            </div>
            <input className="input-field" type="date" value={form.issued_date} onChange={(event) => setForm({ ...form, issued_date: event.target.value })} />
            <input className="input-field" type="date" value={form.due_date} onChange={(event) => setForm({ ...form, due_date: event.target.value })} required />
            <input className="input-field md:col-span-2" placeholder="Notes" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
            <button type="submit" className="btn-primary md:col-span-4" disabled={saving}>
              {saving ? <InlineSpinner /> : null}
              Save tracking record
            </button>
          </form>
        ) : null}

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            { label: "Recovery rate", value: `${metrics?.recovery_rate ?? 0}%`, icon: CheckCircle2, color: "#059669" },
            { label: "Pending", value: money(metrics?.pending_amount ?? totals.pendingAmount, "USD"), icon: Clock, color: "#B45309" },
            { label: "At risk", value: String(metrics?.at_risk_count ?? totals.atRisk), icon: AlertTriangle, color: "#DC2626" },
            { label: "Avg payment", value: `${metrics?.avg_payment_time_days ?? 0}d`, icon: FileText, color: "#0284C7" },
          ].map((item) => (
            <div key={item.label} className="rounded-lg p-4" style={{ backgroundColor: "var(--color-surface)" }}>
              <div className="mb-2 flex items-center gap-2 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                <item.icon size={14} style={{ color: item.color }} />
                {item.label}
              </div>
              <p className="font-mono text-xl font-bold" style={{ color: "var(--color-text)" }}>{item.value}</p>
            </div>
          ))}
        </div>

        {digest ? (
          <div className="grid grid-cols-2 gap-3 rounded-lg p-4 lg:grid-cols-4" style={{ backgroundColor: "var(--color-surface)" }}>
            <p className="text-sm" style={{ color: "var(--color-text)" }}><strong>{digest.payments_detected_this_week}</strong> payments detected</p>
            <p className="text-sm" style={{ color: "var(--color-text)" }}><strong>{digest.valid_excuses_pending}</strong> valid excuses</p>
            <p className="text-sm" style={{ color: "var(--color-text)" }}><strong>{digest.reminders_sent}</strong> reminders sent</p>
            <p className="text-sm" style={{ color: "var(--color-text)" }}><strong>{digest.invoices_at_risk}</strong> invoices at risk</p>
          </div>
        ) : null}

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          <section className="rounded-lg p-4" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-bold" style={{ color: "var(--color-text)" }}>Connections</h2>
                <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>Gmail/Outlook ingestion and Stripe/PayPal reconciliation.</p>
              </div>
              <a href="/dashboard/settings" className="text-xs font-bold text-[var(--color-accent)]">Manage</a>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {(["gmail", "outlook", "stripe", "paypal"] as const).map((provider) => {
                const connected = Boolean(settings?.connections?.[provider]);
                return (
                  <div key={provider} className="rounded-lg p-3" style={{ backgroundColor: "var(--color-surface-high)" }}>
                    <p className="text-xs font-semibold capitalize" style={{ color: "var(--color-text)" }}>{provider}</p>
                    <p className={`mt-1 text-[11px] font-bold ${connected ? "text-emerald-500" : "text-amber-500"}`}>
                      {connected ? "Connected" : "Not connected"}
                    </p>
                  </div>
                );
              })}
            </div>
            {settings?.forward_address ? (
              <div className="mt-3 rounded-lg p-3" style={{ backgroundColor: "var(--color-surface-high)" }}>
                <p className="text-[10px] uppercase opacity-50">Forward invoices to</p>
                <p className="break-all font-mono text-xs" style={{ color: "var(--color-text)" }}>{settings.forward_address}</p>
              </div>
            ) : null}
          </section>

          <section className="rounded-lg p-4" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <h2 className="text-sm font-bold" style={{ color: "var(--color-text)" }}>Client risk scores</h2>
            <p className="mb-3 text-xs" style={{ color: "var(--color-text-secondary)" }}>Risk comes from overdue count, reminders, and payment history.</p>
            <div className="space-y-2">
              {clientScores.slice(0, 4).map((score) => (
                <div key={score.client_email} className="rounded-lg p-3" style={{ backgroundColor: "var(--color-surface-high)" }}>
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold" style={{ color: "var(--color-text)" }}>{score.client_name}</p>
                      <p className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>{score.overdue} overdue · {score.avg_reminders} avg reminders</p>
                    </div>
                    <span className={`font-mono text-sm font-bold ${score.risk_score >= 60 ? "text-red-500" : score.risk_score >= 30 ? "text-amber-500" : "text-emerald-500"}`}>
                      {score.risk_score}
                    </span>
                  </div>
                </div>
              ))}
              {clientScores.length === 0 ? <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>Client scores appear after tracked invoices exist.</p> : null}
            </div>
          </section>

          <section className="rounded-lg p-4" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <h2 className="text-sm font-bold" style={{ color: "var(--color-text)" }}>Email invoice detection</h2>
            <p className="mb-3 text-xs" style={{ color: "var(--color-text-secondary)" }}>Paste a forwarded invoice email to create a reviewable draft.</p>
            <div className="space-y-2">
              <input className="input-field w-full text-xs" placeholder="Subject" value={emailDraftInput.subject} onChange={(event) => setEmailDraftInput({ ...emailDraftInput, subject: event.target.value })} />
              <input className="input-field w-full text-xs" type="email" placeholder="Sender email" value={emailDraftInput.sender_email} onChange={(event) => setEmailDraftInput({ ...emailDraftInput, sender_email: event.target.value })} />
              <input className="input-field w-full text-xs" placeholder="Sender name" value={emailDraftInput.sender_name} onChange={(event) => setEmailDraftInput({ ...emailDraftInput, sender_name: event.target.value })} />
              <textarea className="input-field min-h-24 w-full resize-y text-xs" placeholder="Email body" value={emailDraftInput.body} onChange={(event) => setEmailDraftInput({ ...emailDraftInput, body: event.target.value })} />
              <button type="button" onClick={detectInvoiceEmail} disabled={detectingEmail || !emailDraftInput.sender_email || !emailDraftInput.body} className="btn-secondary w-full justify-center text-xs">
                {detectingEmail ? <InlineSpinner /> : null}
                Detect invoice draft
              </button>
            </div>
            {detectedDraft ? (
              <div className="mt-3 rounded-lg p-3 text-xs" style={{ backgroundColor: "var(--color-surface-high)" }}>
                {detectedDraft.status === "detected" ? (
                  <>
                    <p className="font-semibold" style={{ color: "var(--color-text)" }}>{detectedDraft.client_name} · {money(detectedDraft.amount ?? 0, detectedDraft.currency || "USD")}</p>
                    <p style={{ color: "var(--color-text-secondary)" }}>Due {detectedDraft.due_date || "unknown"} · confidence {Math.round((detectedDraft.confidence ?? 0) * 100)}%</p>
                    <button type="button" onClick={confirmDetectedDraft} disabled={confirmingDraft || !detectedDraft.draft_id || !detectedDraft.due_date} className="btn-primary mt-2 w-full justify-center text-xs">
                      {confirmingDraft ? <InlineSpinner /> : null}
                      Confirm and track
                    </button>
                  </>
                ) : (
                  <p style={{ color: "var(--color-text-secondary)" }}>{detectedDraft.reason || "No invoice detected."}</p>
                )}
              </div>
            ) : null}
          </section>
        </div>

        <div className="dashboard-table-scroll rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
          {invoices.length === 0 ? (
            <div className="p-10">
              <DashboardEmptyState
                icon={<FileText size={24} />}
                title="No tracked invoice records"
                description="Use import, email detection, or the tracking form to start a recovery sequence."
                actionLabel="Add existing invoice record"
                onAction={() => setShowForm(true)}
              />
            </div>
          ) : (
            <table className="w-full min-w-[920px]">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                  {["Client", "Amount", "Due", "Delay", "State", "Next step", "Actions"].map((header) => (
                    <th key={header} className="px-4 py-3 text-left text-xs font-semibold" style={{ color: "var(--color-text-secondary)" }}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {invoices.map((invoice) => {
                  const late = daysOverdue(invoice.due_date);
                  const rowStatus = invoice.status === "pending" && late > 0 ? "overdue" : invoice.cron_paused ? "paused" : invoice.status;
                  return (
                    <tr key={invoice.id} style={{ borderBottom: "1px solid rgba(38,38,38,0.12)" }}>
                      <td className="px-4 py-3">
                        <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>{invoice.client_name}</p>
                        <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{invoice.client_email} · {invoice.invoice_number || "No number"}</p>
                      </td>
                      <td className="px-4 py-3 font-mono text-sm" style={{ color: "var(--color-text)" }}>{money(invoice.amount, invoice.currency)}</td>
                      <td className="px-4 py-3 text-sm" style={{ color: "var(--color-text-secondary)" }}>{invoice.due_date}</td>
                      <td className="px-4 py-3 text-sm font-semibold" style={{ color: late > 0 ? "#DC2626" : "var(--color-text-secondary)" }}>{late}d</td>
                      <td className="px-4 py-3">
                        <span className="rounded-full px-2.5 py-1 text-xs font-semibold" style={statusStyles[rowStatus] || statusStyles.pending}>{rowStatus}</span>
                      </td>
                      <td className="px-4 py-3 text-sm" style={{ color: "var(--color-text-secondary)" }}>{nextStep(invoice)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button type="button" onClick={() => openTimeline(invoice)} className="btn-secondary flex items-center gap-1 px-2 py-1 text-xs">
                            <History size={13} />
                            History
                          </button>
                          {invoice.status !== "paid" ? (
                            <button type="button" onClick={() => mutateInvoice(invoice.id, "mark-paid")} disabled={loadingIds.has(invoice.id)} className="btn-secondary flex items-center gap-1 px-2 py-1 text-xs">
                              <CheckCircle2 size={13} />
                              Paid
                            </button>
                          ) : null}
                          {invoice.status !== "paid" && !invoice.cron_paused ? (
                            <button type="button" onClick={() => mutateInvoice(invoice.id, "pause")} disabled={loadingIds.has(invoice.id)} className="btn-secondary flex items-center gap-1 px-2 py-1 text-xs">
                              <Pause size={13} />
                              Pause
                            </button>
                          ) : invoice.status !== "paid" ? (
                            <button type="button" onClick={() => mutateInvoice(invoice.id, "resume")} disabled={loadingIds.has(invoice.id)} className="btn-secondary flex items-center gap-1 px-2 py-1 text-xs">
                              <Play size={13} />
                              Resume
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {selected ? (
        <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col shadow-2xl" style={{ backgroundColor: "var(--color-surface)", borderLeft: "1px solid var(--color-border)" }}>
          <div className="flex items-start justify-between gap-4 p-5" style={{ borderBottom: "1px solid var(--color-border)" }}>
            <div>
              <h2 className="text-lg font-bold" style={{ color: "var(--color-text)" }}>{selected.client_name}</h2>
              <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{selected.invoice_number || "Tracked invoice"} · {money(selected.amount, selected.currency)}</p>
            </div>
            <button type="button" onClick={() => setSelected(null)} className="btn-secondary px-3 py-1 text-sm">Close</button>
          </div>
          <div className="flex-1 space-y-5 overflow-auto p-5">
            {!timeline ? <DashboardSkeleton rows={3} metrics={0} /> : (
              <>
                <section>
                  <h3 className="mb-2 text-sm font-semibold" style={{ color: "var(--color-text)" }}>Timeline</h3>
                  <div className="grid grid-cols-5 gap-2">
                    {timeline.timeline.map((step) => (
                      <div key={step.day} className="rounded-lg p-3 text-center" style={{ backgroundColor: step.status === "done" ? "rgba(16,185,129,0.12)" : "var(--color-surface-raised)" }}>
                        <p className="text-xs font-semibold" style={{ color: "var(--color-text)" }}>D{step.day}</p>
                        <p className="mt-1 text-[11px]" style={{ color: "var(--color-text-secondary)" }}>{step.name}</p>
                      </div>
                    ))}
                  </div>
                </section>
                <section>
                  <h3 className="mb-2 text-sm font-semibold" style={{ color: "var(--color-text)" }}>Emails sent</h3>
                  <div className="space-y-2">
                    {timeline.emails_sent.length === 0 ? <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>No reminder emails logged yet.</p> : timeline.emails_sent.map((email, index) => (
                      <div key={email.id ?? index} className="rounded-lg p-3" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                        <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>{email.subject}</p>
                        <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{email.status} · {email.sent_at}</p>
                      </div>
                    ))}
                  </div>
                </section>
                <section>
                  <h3 className="mb-2 text-sm font-semibold" style={{ color: "var(--color-text)" }}>Replies and payments</h3>
                  <div className="space-y-2">
                    {timeline.client_replies.map((reply, index) => (
                      <div key={reply.id ?? index} className="rounded-lg p-3" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                        <p className="text-xs font-semibold" style={{ color: "#4F46E5" }}>{reply.intent_label}</p>
                        <p className="text-sm" style={{ color: "var(--color-text)" }}>{reply.text}</p>
                      </div>
                    ))}
                    {timeline.payments_detected.map((payment, index) => (
                      <div key={payment.id ?? index} className="rounded-lg p-3" style={{ backgroundColor: "rgba(16,185,129,0.12)" }}>
                        <p className="text-sm font-semibold" style={{ color: "#059669" }}>{payment.provider}: {money(payment.amount, payment.currency)}</p>
                        <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{payment.status} · {payment.detected_at}</p>
                      </div>
                    ))}
                  </div>
                </section>
              </>
            )}
          </div>
        </div>
      ) : null}
    </>
  );
}
