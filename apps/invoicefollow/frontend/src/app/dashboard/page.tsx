"use client";
import { useState, useEffect } from "react";
import { apiClient, trackEvent } from "@devforge/core";

interface Invoice {
  id: number;
  client_name: string;
  client_email: string;
  amount: number;
  due_date: string;
  status: "pending" | "paid" | "overdue";
  reminders_sent: number;
}

type DebtorRisk = "green" | "yellow" | "red";

interface DebtorProfile {
  client_name: string;
  client_email: string;
  risk: DebtorRisk;
  totalOwed: number;
  invoices: Invoice[];
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
  green:  { label: "Paga a tiempo",     bg: "rgba(16,185,129,0.12)", border: "rgba(16,185,129,0.3)", text: "#10B981", dot: "#10B981" },
  yellow: { label: "Suele tardar",      bg: "rgba(245,158,11,0.12)", border: "rgba(245,158,11,0.3)", text: "#F59E0B", dot: "#F59E0B" },
  red:    { label: "Riesgo de no pago", bg: "rgba(239,68,68,0.12)",  border: "rgba(239,68,68,0.3)",  text: "#EF4444", dot: "#EF4444" },
};

const statusColors: Record<string, { backgroundColor: string; color: string }> = {
  pending: { backgroundColor: "rgba(245,158,11,0.15)", color: "#F59E0B" },
  paid:    { backgroundColor: "rgba(16,185,129,0.15)", color: "#10B981" },
  overdue: { backgroundColor: "rgba(239,68,68,0.15)",  color: "#EF4444" },
};

export default function DashboardPage() {
  const [invoices, setInvoices]     = useState<Invoice[]>([]);
  const [showForm, setShowForm]     = useState(false);
  const [view, setView]             = useState<"semaforo" | "lista">("semaforo");
  const [loadingIds, setLoadingIds] = useState<Set<number>>(new Set());
  const [form, setForm]             = useState({ client_name: "", client_email: "", amount: "", due_date: "" });

  useEffect(() => {
    apiClient.get<Invoice[]>("/invoices/list").then(({ data }) => setInvoices(data)).catch(() => {});
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    trackEvent("feature_used", { feature_name: "add_invoice" });
    const { data } = await apiClient.post<Invoice>("/invoices", {
      client_name: form.client_name, client_email: form.client_email,
      amount: parseFloat(form.amount), due_date: form.due_date,
    });
    setInvoices(prev => [data, ...prev]);
    setForm({ client_name: "", client_email: "", amount: "", due_date: "" });
    setShowForm(false);
  };

  const handleMarkPaid = async (id: number) => {
    setLoadingIds(prev => new Set(prev).add(id));
    trackEvent("feature_used", { feature_name: "mark_invoice_paid" });
    try {
      await apiClient.put(`/invoices/${id}/mark-paid`);
      setInvoices(prev => prev.map(inv => inv.id === id ? { ...inv, status: "paid" } : inv));
    } catch { alert("Error al marcar como pagada"); }
    finally { setLoadingIds(prev => { const s = new Set(prev); s.delete(id); return s; }); }
  };

  const debtorMap = new Map<string, DebtorProfile>();
  invoices.forEach(inv => {
    const key = inv.client_email || inv.client_name;
    if (!debtorMap.has(key)) debtorMap.set(key, { client_name: inv.client_name, client_email: inv.client_email, risk: "green", totalOwed: 0, invoices: [] });
    const p = debtorMap.get(key)!;
    p.invoices.push(inv);
    if (inv.status !== "paid") p.totalOwed += inv.amount;
  });
  debtorMap.forEach(p => { p.risk = getRisk(p.invoices); });
  const order = { red: 0, yellow: 1, green: 2 };
  const debtors = Array.from(debtorMap.values()).sort((a, b) => order[a.risk] - order[b.risk]);

  const totalPending = invoices.filter(i => i.status !== "paid").reduce((s, i) => s + i.amount, 0);
  const overdueCnt   = invoices.filter(i => i.status === "overdue").length;
  const redDebtors   = debtors.filter(d => d.risk === "red").length;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "var(--color-text)" }}>Invoices</h1>
          <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
            {invoices.length} facturas &middot; <span className="font-mono font-semibold" style={{ color: "var(--color-accent)" }}>${totalPending.toFixed(2)}</span> pendiente
          </p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary">+ Nueva factura</button>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="p-4 rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
          <p className="text-xs mb-1" style={{ color: "var(--color-text-secondary)" }}>Total pendiente</p>
          <p className="text-xl font-bold font-mono" style={{ color: "var(--color-accent)" }}>${totalPending.toFixed(2)}</p>
        </div>
        <div className="p-4 rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
          <p className="text-xs mb-1" style={{ color: "var(--color-text-secondary)" }}>Vencidas</p>
          <p className="text-xl font-bold font-mono" style={{ color: "#EF4444" }}>{overdueCnt}</p>
        </div>
        <div className="p-4 rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
          <p className="text-xs mb-1" style={{ color: "var(--color-text-secondary)" }}>Clientes en riesgo</p>
          <p className="text-xl font-bold font-mono" style={{ color: "#EF4444" }}>{redDebtors}</p>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleAdd} className="p-6 rounded-lg mb-6 grid grid-cols-1 md:grid-cols-5 gap-4 items-end" style={{ backgroundColor: "var(--color-surface)" }}>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Cliente</label>
            <input type="text" value={form.client_name} onChange={e => setForm({ ...form, client_name: e.target.value })} className="input-field" required />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Email cliente</label>
            <input type="email" value={form.client_email} onChange={e => setForm({ ...form, client_email: e.target.value })} className="input-field" required />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Monto ($)</label>
            <input type="number" step="0.01" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} className="input-field" required />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Vencimiento</label>
            <input type="date" value={form.due_date} onChange={e => setForm({ ...form, due_date: e.target.value })} className="input-field" required />
          </div>
          <button type="submit" className="btn-primary">Guardar</button>
        </form>
      )}

      <div className="flex gap-2 mb-6">
        <button onClick={() => setView("semaforo")} className="text-xs font-medium px-4 py-2 rounded-md transition-colors"
          style={{ backgroundColor: view === "semaforo" ? "var(--color-accent-dim)" : "var(--color-surface)", color: view === "semaforo" ? "var(--color-accent)" : "var(--color-text-secondary)" }}>
          Semaforo de deudores
        </button>
        <button onClick={() => setView("lista")} className="text-xs font-medium px-4 py-2 rounded-md transition-colors"
          style={{ backgroundColor: view === "lista" ? "var(--color-accent-dim)" : "var(--color-surface)", color: view === "lista" ? "var(--color-accent)" : "var(--color-text-secondary)" }}>
          Lista de facturas
        </button>
      </div>

      {view === "semaforo" && (
        <div className="space-y-4">
          {debtors.length === 0 && (
            <div className="p-12 text-center rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
              <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>Aun no hay clientes. Agrega tu primera factura.</p>
            </div>
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
                        <p className="text-xs mt-0.5" style={{ color: "var(--color-text-secondary)" }}>{debtor.client_email} &middot; {debtor.invoices.length} factura(s)</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold font-mono" style={{ color: cfg.text }}>${debtor.totalOwed.toFixed(2)}</p>
                        <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>pendiente</p>
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
              <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>No hay facturas. Crea la primera arriba.</p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                  {["Cliente", "Monto", "Vencimiento", "Estado", "Recordatorios", ""].map((h, i) => (
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
                    <td className="px-4 py-3"><span className="text-xs font-medium px-2.5 py-1 rounded-full" style={statusColors[inv.status]}>{inv.status}</span></td>
                    <td className="px-4 py-3 text-sm font-mono" style={{ color: "var(--color-text-secondary)" }}>{inv.reminders_sent}</td>
                    <td className="px-4 py-3 text-right">
                      {(inv.status === "pending" || inv.status === "overdue") && (
                        <button onClick={() => handleMarkPaid(inv.id)} disabled={loadingIds.has(inv.id)}
                          className="text-xs font-medium px-3 py-1.5 rounded transition-colors"
                          style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text)", opacity: loadingIds.has(inv.id) ? 0.5 : 1 }}>
                          {loadingIds.has(inv.id) ? "Procesando..." : "Marcar pagada"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
