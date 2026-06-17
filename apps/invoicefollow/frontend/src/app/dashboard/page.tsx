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
import { Download, ChevronDown, Sparkles, Loader2, Copy, Check, X, Upload } from "lucide-react";

interface Invoice {
  id: number;
  client_name: string;
  client_email: string;
  amount: number;
  due_date: string;
  status: "pending" | "paid" | "overdue";
  reminders_sent: number;
  payment_promise_date?: string | null;
  cron_paused?: boolean;
}

type DebtorRisk = "green" | "yellow" | "red";

interface DebtorProfile {
  client_name: string;
  client_email: string;
  risk: DebtorRisk;
  totalOwed: number;
  invoices: Invoice[];
}

interface InvoiceSummary {
  pending_amount: number;
  overdue_amount: number;
  promised_amount: number;
  cash_at_risk: number;
  overdue_count: number;
}

function getRisk(invoices: Invoice[]): DebtorRisk {
  const overdue = invoices.filter(i => i.status === "overdue").length;
  const total = invoices.length;
  const avgReminders = invoices.reduce((s, i) => s + i.reminders_sent, 0) / (total || 1);
  if (overdue === 0 && avgReminders < 1) return "green";
  if (overdue >= 1 && overdue < total * 0.5) return "yellow";
  return "red";
}

const riskConfig = {
  green:  { label: "Pays on time",     bg: "rgba(16,185,129,0.12)", border: "rgba(16,185,129,0.3)", text: "#10B981", dot: "#10B981" },
  yellow: { label: "Often pays late",  bg: "rgba(245,158,11,0.12)", border: "rgba(245,158,11,0.3)", text: "#F59E0B", dot: "#F59E0B" },
  red:    { label: "At risk",          bg: "rgba(239,68,68,0.12)",  border: "rgba(239,68,68,0.3)",  text: "#EF4444", dot: "#EF4444" },
};

const statusColors: Record<string, { backgroundColor: string; color: string }> = {
  pending: { backgroundColor: "rgba(245,158,11,0.15)", color: "#F59E0B" },
  paid:    { backgroundColor: "rgba(16,185,129,0.15)", color: "#10B981" },
  overdue: { backgroundColor: "rgba(239,68,68,0.15)",  color: "#EF4444" },
};

export default function DashboardPage() {
  const [invoices, setInvoices]     = useState<Invoice[]>([]);
  const [scores, setScores]         = useState<any[]>([]);
  const [showForm, setShowForm]     = useState(false);
  const [view, setView]             = useState<"semaforo" | "lista">("semaforo");
  const [loadingIds, setLoadingIds] = useState<Set<number>>(new Set());
  const [form, setForm]             = useState({ client_name: "", client_email: "", amount: "", due_date: "" });
  const [exportOpen, setExportOpen] = useState(false);
  const [aiTonePanel, setAiTonePanel] = useState<null | { invoiceId: number; loading: boolean; result: any }>(null);
  const [copiedTone, setCopiedTone] = useState(false);
  const [summary, setSummary] = useState<InvoiceSummary | null>(null);
  const [importing, setImporting] = useState(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const [savingInvoice, setSavingInvoice] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [toast, setToast] = useState<DashboardToast | null>(null);
  const exportRef = useRef<HTMLDivElement>(null);

  const showToast = useCallback((nextToast: DashboardToast) => {
    setToast(nextToast);
    window.setTimeout(() => setToast(null), 4500);
  }, []);

  const refreshInvoices = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    const [invoiceResult, scoreResult, summaryResult] = await Promise.allSettled([
      apiClient.get<Invoice[]>("/invoices/list"),
      apiClient.get<any[]>("/invoices/client-scores"),
      apiClient.get<InvoiceSummary>("/invoices/summary"),
    ]);

    if (invoiceResult.status === "fulfilled") setInvoices(invoiceResult.value.data);
    if (scoreResult.status === "fulfilled") setScores(scoreResult.value.data);
    if (summaryResult.status === "fulfilled") setSummary(summaryResult.value.data);
    if (invoiceResult.status === "rejected" && scoreResult.status === "rejected" && summaryResult.status === "rejected") {
      setLoadError(true);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    refreshInvoices();
  }, [refreshInvoices]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) setExportOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingInvoice(true);
    trackEvent("feature_used", { feature_name: "add_invoice" });
    try {
      const { data } = await apiClient.post<Invoice>("/invoices", {
        client_name: form.client_name, client_email: form.client_email,
        amount: parseFloat(form.amount), due_date: form.due_date,
      });
      setInvoices(prev => [data, ...prev]);
      setForm({ client_name: "", client_email: "", amount: "", due_date: "" });
      setShowForm(false);
      showToast({ tone: "success", message: `${data.client_name}'s invoice was saved.` });
      refreshInvoices();
    } catch (e: any) {
      showToast({ tone: "error", message: e.detail || "We could not save this invoice. Check the email, amount, and due date." });
    } finally {
      setSavingInvoice(false);
    }
  };

  const handleImportFile = async (fileInput: File) => {
    setImporting(true);
    setImportMessage(null);
    trackEvent("feature_used", { feature_name: "import_invoices", format: fileInput.name.split(".").pop() });
    try {
      const formData = new FormData();
      formData.append("file", fileInput);
      const { data } = await uploadFile<{ created: number; invoices: Invoice[] }>("/invoices/import-csv", formData);
      setInvoices(prev => [...data.invoices, ...prev]);
      setImportMessage(`${data.created} invoices imported`);
      showToast({ tone: "success", message: `${data.created} invoices imported.` });
      refreshInvoices();
    } catch (e: any) {
      showToast({ tone: "error", message: e.detail || "We could not import your invoices. Check that the file is CSV or XLSX." });
    } finally {
      setImporting(false);
    }
  };

  const openImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".csv,.xlsx,.xls";
    input.onchange = e => {
      const f = (e.target as HTMLInputElement).files?.[0];
      if (f) handleImportFile(f);
    };
    input.click();
  };

  const handlePauseReminders = async (id: number) => {
    setLoadingIds(prev => new Set(prev).add(id));
    trackEvent("feature_used", { feature_name: "pause_invoice_reminders" });
    try {
      const { data } = await apiClient.put<{ payment_promise_date: string }>(`/invoices/${id}/pause-reminders`);
      setInvoices(prev => prev.map(inv => inv.id === id ? { ...inv, cron_paused: true, payment_promise_date: data.payment_promise_date } : inv));
      showToast({ tone: "success", message: "Promise to pay saved. Reminders are paused for this invoice." });
    } catch {
      showToast({ tone: "error", message: "We could not save the promise to pay. Retry from the invoice row." });
    }
    finally { setLoadingIds(prev => { const s = new Set(prev); s.delete(id); return s; }); }
  };

  const handleMarkPaid = async (id: number) => {
    setLoadingIds(prev => new Set(prev).add(id));
    trackEvent("feature_used", { feature_name: "mark_invoice_paid" });
    try {
      await apiClient.put(`/invoices/${id}/mark-paid`);
      setInvoices(prev => prev.map(inv => inv.id === id ? { ...inv, status: "paid" } : inv));
      showToast({ tone: "success", message: "Invoice marked as paid." });
    } catch {
      showToast({ tone: "error", message: "We could not mark this invoice as paid. Retry from the invoice row." });
    }
    finally { setLoadingIds(prev => { const s = new Set(prev); s.delete(id); return s; }); }
  };

  const handleExport = async (format: "csv" | "xlsx" | "json") => {
    setExportOpen(false);
    trackEvent("feature_used", { feature_name: "export_invoices", format });
    try {
      await downloadFile(`/invoices/export?format=${format}`, `invoicefollow_export.${format}`);
      showToast({ tone: "success", message: `Your invoices export started as ${format.toUpperCase()}.` });
    } catch {
      showToast({ tone: "error", message: "We could not export your invoices. Retry from the export menu." });
    }
  };

  const handleAiTone = async (inv: Invoice) => {
    setAiTonePanel({ invoiceId: inv.id, loading: true, result: null });
    trackEvent("feature_used", { feature_name: "ai_tone_invoice" });
    try {
      const { data } = await apiClient.post(`/invoices/${inv.id}/ai-tone`, {});
      setAiTonePanel({ invoiceId: inv.id, loading: false, result: data });
      showToast({ tone: "success", message: `A follow-up message for ${inv.client_name} is ready.` });
    } catch {
      setAiTonePanel(null);
      showToast({ tone: "error", message: "We could not write that follow-up. Retry from the invoice row." });
    }
  };

  const handleCopyTone = () => {
    if (!aiTonePanel?.result) return;
    const { greeting, body, call_to_action } = aiTonePanel.result;
    navigator.clipboard.writeText(`${greeting}\n\n${body}\n\n${call_to_action}`);
    setCopiedTone(true);
    setTimeout(() => setCopiedTone(false), 2000);
  };

  const debtorMap = new Map<string, DebtorProfile>();
  invoices.forEach(inv => {
    const key = inv.client_email || inv.client_name;
    if (!debtorMap.has(key)) debtorMap.set(key, { client_name: inv.client_name, client_email: inv.client_email, risk: "green", totalOwed: 0, invoices: [] });
    const p = debtorMap.get(key)!;
    p.invoices.push(inv);
    if (inv.status !== "paid") p.totalOwed += inv.amount;
  });
  debtorMap.forEach(p => {
    const score = scores.find(s => s.client_email === p.client_email);
    if (score) {
      p.risk = score.risk_label === "alto" ? "red" : score.risk_label === "medio" ? "yellow" : "green";
    } else {
      p.risk = getRisk(p.invoices);
    }
  });
  const order = { red: 0, yellow: 1, green: 2 };
  const debtors = Array.from(debtorMap.values()).sort((a, b) => order[a.risk] - order[b.risk]);

  const totalPending = invoices.filter(i => i.status !== "paid").reduce((s, i) => s + i.amount, 0);
  const overdueCnt   = invoices.filter(i => i.status === "overdue").length;
  const redDebtors   = debtors.filter(d => d.risk === "red").length;

  return (
    <>
      <ActionToast toast={toast} onDismiss={() => setToast(null)} />
      <div>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "var(--color-text)" }}>Money owed to you</h1>
            <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
              {invoices.length} invoices &middot; <span className="font-mono font-semibold" style={{ color: "var(--color-accent)" }}>${totalPending.toFixed(2)}</span> still owed
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative" ref={exportRef}>
              <button onClick={() => setExportOpen(!exportOpen)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all"
                style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)" }}>
                <Download size={14} /><span>Export invoices</span>
                <ChevronDown size={12} className={`transition-transform ${exportOpen ? "rotate-180" : ""}`} />
              </button>
              {exportOpen && (
                <div className="absolute right-0 top-full mt-2 w-44 rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200"
                  style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                  {(["csv", "xlsx", "json"] as const).map(f => (
                    <button key={f} onClick={() => handleExport(f)}
                      className="w-full text-left px-4 py-2.5 text-sm hover:bg-black/5 transition-colors"
                      style={{ color: "var(--color-text)" }}>
                      {f.toUpperCase()} - {f === "csv" ? "Spreadsheet" : f === "xlsx" ? "Excel" : "JSON"}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button onClick={openImport} disabled={importing}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all"
              style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)", opacity: importing ? 0.7 : 1 }}>
              {importing ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
              <span>{importing ? "Importing invoices" : "Import invoices"}</span>
            </button>
            <button onClick={() => setShowForm(!showForm)} className="btn-primary">Add invoice</button>
          </div>
        </div>

        {importMessage && (
          <div className="p-3 rounded-lg mb-6 text-sm text-emerald-500"
            style={{ backgroundColor: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.25)" }}>
            {importMessage}
          </div>
        )}

        {loadError && (
          <div className="mb-6">
            <InlineErrorState
              title="We could not load your invoices"
              description="Your invoice dashboard did not load. Retry now, and contact support if it keeps happening."
              onRetry={refreshInvoices}
            />
          </div>
        )}

        {loading && invoices.length === 0 && <DashboardSkeleton rows={4} metrics={3} />}

        {!loading && !loadError && invoices.length === 0 && (
          <WelcomeSteps
            title="Add your first invoice"
            description="Track what clients owe you, see invoices due today, and pause reminders when someone promises to pay."
            steps={[
              "Add one invoice manually or import CSV/XLSX.",
              "Review what is owed, overdue today, and cash at risk.",
              "Mark invoices paid or save a promise to pay when a client replies.",
            ]}
            actionLabel="Add your first invoice"
            onAction={() => setShowForm(true)}
          />
        )}

        {!loading && (
        <>


        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="p-4 rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
            <p className="text-xs mb-1" style={{ color: "var(--color-text-secondary)" }}>Still owed</p>
            <p className="text-xl font-bold font-mono" style={{ color: "var(--color-accent)" }}>${(summary?.pending_amount ?? totalPending).toFixed(2)}</p>
          </div>
          <div className="p-4 rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
            <p className="text-xs mb-1" style={{ color: "var(--color-text-secondary)" }}>Due today or late</p>
            <p className="text-xl font-bold font-mono" style={{ color: "#EF4444" }}>{summary?.overdue_count ?? overdueCnt}</p>
          </div>
          <div className="p-4 rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
            <p className="text-xs mb-1" style={{ color: "var(--color-text-secondary)" }}>Cash at risk</p>
            <p className="text-xl font-bold font-mono" style={{ color: "#EF4444" }}>${(summary?.cash_at_risk ?? 0).toFixed(2)}</p>
          </div>
        </div>

        {summary && summary.promised_amount > 0 && (
          <div className="p-4 rounded-lg mb-6 flex items-center justify-between gap-4"
            style={{ backgroundColor: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.25)" }}>
            <div>
              <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Promises to pay saved</p>
              <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>Amount paused because clients promised to pay.</p>
            </div>
            <p className="text-lg font-mono font-bold text-indigo-400">${summary.promised_amount.toFixed(2)}</p>
          </div>
        )}

        {showForm && (
          <form onSubmit={handleAdd} className="p-6 rounded-lg mb-6 grid grid-cols-1 md:grid-cols-5 gap-4 items-end" style={{ backgroundColor: "var(--color-surface)" }}>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Client</label>
              <input type="text" value={form.client_name} onChange={e => setForm({ ...form, client_name: e.target.value })} className="input-field" required />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Client email</label>
              <input type="email" value={form.client_email} onChange={e => setForm({ ...form, client_email: e.target.value })} className="input-field" required />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Amount owed ($)</label>
              <input type="number" step="0.01" min="0.01" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} className="input-field" required />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Due date</label>
              <input type="date" value={form.due_date} onChange={e => setForm({ ...form, due_date: e.target.value })} className="input-field" required />
            </div>
            <button type="submit" disabled={savingInvoice} className="btn-primary">
              {savingInvoice ? <InlineSpinner /> : null}
              {savingInvoice ? "Saving invoice" : "Save invoice"}
            </button>
          </form>
        )}

        <div className="flex gap-2 mb-6">
          <button onClick={() => setView("semaforo")} className="text-xs font-medium px-4 py-2 rounded-md transition-colors"
            style={{ backgroundColor: view === "semaforo" ? "var(--color-accent-dim)" : "var(--color-surface)", color: view === "semaforo" ? "var(--color-accent)" : "var(--color-text-secondary)" }}>
            Clients by payment risk
          </button>
          <button onClick={() => setView("lista")} className="text-xs font-medium px-4 py-2 rounded-md transition-colors"
            style={{ backgroundColor: view === "lista" ? "var(--color-accent-dim)" : "var(--color-surface)", color: view === "lista" ? "var(--color-accent)" : "var(--color-text-secondary)" }}>
            Invoice list
          </button>
        </div>

        {view === "semaforo" && (
          <div className="space-y-4">
            {debtors.length === 0 && (
              <DashboardEmptyState
                icon={<Sparkles size={24} />}
                title="Add your first client"
                description="Create one invoice to see what they owe you and whether reminders need attention."
                actionLabel="Add an invoice"
                onAction={() => setShowForm(true)}
              />
            )}
            {(["red", "yellow", "green"] as DebtorRisk[]).map(risk => {
              const group = debtors.filter(d => d.risk === risk);
              if (group.length === 0) return null;
              const cfg = riskConfig[risk];
              return (
                <div key={risk}>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: cfg.dot }} />
                    <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: cfg.text }}>{cfg.label} ({group.length})</p>
                  </div>
                  <div className="space-y-2">
                    {group.map(debtor => (
                      <div key={debtor.client_email} className="p-4 rounded-lg flex items-center justify-between"
                        style={{ backgroundColor: cfg.bg, border: `1px solid ${cfg.border}` }}>
                        <div>
                          <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>{debtor.client_name}</p>
                          <p className="text-xs mt-0.5" style={{ color: "var(--color-text-secondary)" }}>{debtor.client_email} &middot; {debtor.invoices.length} invoice(s)</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-bold font-mono" style={{ color: cfg.text }}>${debtor.totalOwed.toFixed(2)}</p>
                          <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>still owed</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {view === "lista" && (
          <div className="rounded-lg overflow-hidden" style={{ backgroundColor: "var(--color-surface)" }}>
            {invoices.length === 0 ? (
              <div className="p-12 text-center">
                <DashboardEmptyState
                  icon={<Upload size={24} />}
                  title="Add your first invoice"
                  description="Once you add invoices, this list shows who owes you money, due dates, and promises to pay."
                  actionLabel="Add an invoice"
                  onAction={() => setShowForm(true)}
                />
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                    {["Client", "Amount owed", "Due date", "State", "Reminders", ""].map((h, i) => (
                      <th key={i} className="text-left text-xs font-medium uppercase tracking-wide px-4 py-3" style={{ color: "var(--color-text-secondary)" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {invoices.map(inv => (
                    <tr key={inv.id} style={{ borderBottom: "1px solid rgba(38,38,38,0.15)" }}>
                      <td className="px-4 py-3">
                        <p className="text-sm font-medium" style={{ color: "var(--color-text)" }}>{inv.client_name}</p>
                        <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{inv.client_email}</p>
                      </td>
                      <td className="px-4 py-3 text-sm font-mono" style={{ color: "var(--color-text)" }}>${inv.amount.toFixed(2)}</td>
                      <td className="px-4 py-3 text-sm" style={{ color: "var(--color-text-secondary)" }}>{inv.due_date}</td>
                      <td className="px-4 py-3">
                        <span className="text-xs font-medium px-2.5 py-1 rounded-full" style={statusColors[inv.status]}>{inv.status}</span>
                        {inv.cron_paused && (
                          <span className="text-[10px] font-bold px-1.5 py-0.5 ml-2 rounded bg-indigo-500/10 text-indigo-500 uppercase tracking-wider">
                            PROMISED
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm font-mono" style={{ color: "var(--color-text-secondary)" }}>{inv.reminders_sent}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {(inv.status === "pending" || inv.status === "overdue") && (
                            <button onClick={() => handleAiTone(inv)}
                              disabled={aiTonePanel?.invoiceId === inv.id && aiTonePanel.loading}
                              className="text-xs font-medium px-3 py-1.5 rounded transition-all flex items-center gap-1.5"
                              style={{ backgroundColor: "rgba(99,102,241,0.1)", color: "#6366F1" }}>
                              {aiTonePanel?.invoiceId === inv.id && aiTonePanel.loading
                                ? <Loader2 size={12} className="animate-spin" />
                                : <Sparkles size={12} />}
                              Write follow-up
                            </button>
                          )}
                          {(inv.status === "pending" || inv.status === "overdue") && !inv.cron_paused && (
                            <button onClick={() => handlePauseReminders(inv.id)} disabled={loadingIds.has(inv.id)}
                              className="text-xs font-medium px-3 py-1.5 rounded transition-colors"
                              title="Pause reminders (promise to pay)"
                              style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-secondary)", opacity: loadingIds.has(inv.id) ? 0.5 : 1 }}>
                              Save promise
                            </button>
                          )}
                          {(inv.status === "pending" || inv.status === "overdue") && (
                            <button onClick={() => handleMarkPaid(inv.id)} disabled={loadingIds.has(inv.id)}
                              className="text-xs font-medium px-3 py-1.5 rounded transition-colors"
                              style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text)", opacity: loadingIds.has(inv.id) ? 0.5 : 1 }}>
                              {loadingIds.has(inv.id) ? "Updating" : "Mark paid"}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
        </>
        )}
      </div>

      {/* AI Tone Side Panel — Skill: gemini-api-dev */}
      {aiTonePanel && (
        <div className="fixed inset-y-0 right-0 w-full max-w-md shadow-2xl z-50 flex flex-col animate-in slide-in-from-right-4 duration-300"
          style={{ backgroundColor: "var(--color-surface)", borderLeft: "1px solid var(--color-border)" }}>
          <div className="p-6 border-b border-[var(--color-border)] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles size={18} className="text-indigo-400" />
              <h2 className="text-sm font-bold uppercase tracking-wider">AI Tone Generator</h2>
            </div>
            <button onClick={() => setAiTonePanel(null)} className="p-1.5 rounded-lg hover:bg-black/10 transition-colors">
              <X size={18} className="opacity-50" />
            </button>
          </div>

          {aiTonePanel.loading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <Loader2 size={32} className="animate-spin text-indigo-400 mx-auto mb-3" />
                <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>Writing a follow-up for this invoice...</p>
              </div>
            </div>
          ) : aiTonePanel.result && (
            <div className="flex-1 overflow-auto p-6 space-y-5">
              {(() => {
                const toneColors: Record<string, string> = {
                  cordial: "#10B981", amable: "#6366F1", urgente: "#F59E0B", formal: "#EF4444", template: "#A3A3A3"
                };
                const toneLabels: Record<string, string> = {
                  cordial: "Friendly", amable: "Warm", urgente: "Urgent", formal: "Formal", template: "Template"
                };
                const color = toneColors[aiTonePanel.result.tone_label] || "#A3A3A3";
                return (
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider"
                      style={{ backgroundColor: `${color}15`, color }}>
                      {aiTonePanel.result.tone_label} · {aiTonePanel.result.days_overdue}d overdue
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded"
                      style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-secondary)" }}>
                      {aiTonePanel.result.engine === "gemini" ? "Gemini" : "Template"}
                    </span>
                  </div>
                );
              })()}

              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest mb-2 opacity-50">Subject</p>
                <p className="text-sm font-medium p-3 rounded-lg" style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text)" }}>
                  {aiTonePanel.result.subject}
                </p>
              </div>

              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest mb-2 opacity-50">Message</p>
                <div className="p-4 rounded-lg space-y-3" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                  <p className="text-sm font-medium" style={{ color: "var(--color-text)" }}>{aiTonePanel.result.greeting}</p>
                  <p className="text-sm whitespace-pre-wrap" style={{ color: "var(--color-text)" }}>{aiTonePanel.result.body}</p>
                  <p className="text-sm font-medium text-indigo-400">{aiTonePanel.result.call_to_action}</p>
                </div>
              </div>
            </div>
          )}

          {!aiTonePanel.loading && aiTonePanel.result && (
            <div className="p-6 border-t border-[var(--color-border)]">
              <button onClick={handleCopyTone}
                className="w-full py-3 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all"
                style={{ backgroundColor: "var(--color-primary)", color: "#000" }}>
                {copiedTone ? <Check size={16} /> : <Copy size={16} />}
                {copiedTone ? "Copied to clipboard" : "Copy full message"}
              </button>
            </div>
          )}
        </div>
      )}
    </>
  );
}

