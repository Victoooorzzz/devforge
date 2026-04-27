"use client";
import { useState, useEffect } from "react";
import { apiClient, trackEvent } from "@devforge/core";

interface Invoice {
  id: number;
  client_name: string;
  amount: number;
  due_date: string;
  status: "pending" | "paid" | "overdue";
  reminders_sent: number;
}

export default function DashboardPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ client_name: "", amount: "", due_date: "" });

  useEffect(() => {
    apiClient.get<Invoice[]>("/invoices/list").then(({ data }) => setInvoices(data)).catch(() => {});
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    trackEvent("feature_used", { feature_name: "add_invoice" });
    const { data } = await apiClient.post<Invoice>("/invoices", { client_name: form.client_name, amount: parseFloat(form.amount), due_date: form.due_date });
    setInvoices((prev) => [data, ...prev]);
    setForm({ client_name: "", amount: "", due_date: "" });
    setShowForm(false);
  };

  const statusColors: Record<string, { backgroundColor: string; color: string }> = {
    pending: { backgroundColor: "rgba(245,158,11,0.15)", color: "#F59E0B" },
    paid: { backgroundColor: "rgba(16,185,129,0.15)", color: "#10B981" },
    overdue: { backgroundColor: "rgba(239,68,68,0.15)", color: "#EF4444" },
  };

  const totalPending = invoices.filter((i) => i.status !== "paid").reduce((s, i) => s + i.amount, 0);

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "var(--color-text)" }}>Invoices</h1>
          <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
            {invoices.length} invoices · <span className="font-mono font-semibold" style={{ color: "var(--color-accent)" }}>${totalPending.toFixed(2)}</span> outstanding
          </p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary">+ Add Invoice</button>
      </div>

      {showForm && (
        <form onSubmit={handleAdd} className="p-6 rounded-lg mb-8 grid grid-cols-1 md:grid-cols-4 gap-4 items-end" style={{ backgroundColor: "var(--color-surface)" }}>
          <div><label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Client</label><input value={form.client_name} onChange={(e) => setForm({ ...form, client_name: e.target.value })} className="input-field" required /></div>
          <div><label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Amount ($)</label><input type="number" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} className="input-field" required /></div>
          <div><label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Due Date</label><input type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} className="input-field" required /></div>
          <button type="submit" className="btn-primary">Save</button>
        </form>
      )}

      <div className="rounded-lg overflow-hidden" style={{ backgroundColor: "var(--color-surface)" }}>
        <table className="w-full">
          <thead><tr style={{ borderBottom: "1px solid var(--color-border)" }}>
            {["Client", "Amount", "Due Date", "Status", "Reminders"].map((h) => (
              <th key={h} className="text-left text-xs font-medium uppercase tracking-wide px-4 py-3" style={{ color: "var(--color-text-secondary)" }}>{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.id} style={{ borderBottom: "1px solid rgba(38,38,38,0.15)" }}>
                <td className="px-4 py-3 text-sm font-medium" style={{ color: "var(--color-text)" }}>{inv.client_name}</td>
                <td className="px-4 py-3 text-sm font-mono" style={{ color: "var(--color-text)" }}>${inv.amount.toFixed(2)}</td>
                <td className="px-4 py-3 text-sm" style={{ color: "var(--color-text-secondary)" }}>{inv.due_date}</td>
                <td className="px-4 py-3"><span className="text-xs font-medium px-2.5 py-1 rounded-full" style={{ ...statusColors[inv.status] }}>{inv.status}</span></td>
                <td className="px-4 py-3 text-sm font-mono" style={{ color: "var(--color-text-secondary)" }}>{inv.reminders_sent}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
