"use client";
import { useState, useEffect } from "react";
import { apiClient, trackEvent } from "@devforge/core";

interface TrackedUrl {
  id: number;
  url: string;
  label: string;
  current_price: number | null;
  previous_price: number | null;
  last_checked: string | null;
  status: "active" | "error";
}

export default function DashboardPage() {
  const [trackers, setTrackers] = useState<TrackedUrl[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ url: "", label: "" });

  useEffect(() => {
    apiClient.get<TrackedUrl[]>("/trackers/list").then(({ data }) => setTrackers(data)).catch(() => {});
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    trackEvent("feature_used", { feature_name: "add_tracker" });
    const { data } = await apiClient.post<TrackedUrl>("/trackers", { url: form.url, label: form.label });
    setTrackers((prev) => [data, ...prev]);
    setForm({ url: "", label: "" });
    setShowForm(false);
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("¿Estás seguro de que deseas eliminar este producto?")) return;
    trackEvent("feature_used", { feature_name: "delete_tracker" });
    try {
      await apiClient.delete(`/trackers/${id}`);
      setTrackers((prev) => prev.filter((t) => t.id !== id));
      alert("Producto eliminado");
    } catch (err: any) {
      alert("Error al eliminar producto");
    }
  };

  const getPriceChange = (curr: number | null, prev: number | null) => {
    if (!curr || !prev || prev === 0) return null;
    return ((curr - prev) / prev * 100).toFixed(1);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "var(--color-text)" }}>Trackers</h1>
          <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{trackers.length} URLs monitored</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary">+ Add URL</button>
      </div>

      {showForm && (
        <form onSubmit={handleAdd} className="p-6 rounded-lg mb-8 grid grid-cols-1 md:grid-cols-3 gap-4 items-end" style={{ backgroundColor: "var(--color-surface)" }}>
          <div className="md:col-span-1"><label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Label</label><input value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} className="input-field" placeholder="e.g. Competitor Pro Plan" required /></div>
          <div className="md:col-span-1"><label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>URL</label><input type="url" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} className="input-field" placeholder="https://..." required /></div>
          <button type="submit" className="btn-primary">Track</button>
        </form>
      )}

      <div className="rounded-lg overflow-hidden" style={{ backgroundColor: "var(--color-surface)" }}>
        <table className="w-full">
          <thead><tr style={{ borderBottom: "1px solid var(--color-border)" }}>
            {["Label", "Current Price", "Change", "Last Checked", "Status", ""].map((h, i) => (
              <th key={i} className="text-left text-xs font-medium uppercase tracking-wide px-4 py-3" style={{ color: "var(--color-text-secondary)" }}>{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {trackers.map((t) => {
              const change = getPriceChange(t.current_price, t.previous_price);
              return (
                <tr key={t.id} style={{ borderBottom: "1px solid rgba(38,38,38,0.15)" }}>
                  <td className="px-4 py-3"><p className="text-sm font-medium" style={{ color: "var(--color-text)" }}>{t.label}</p><p className="text-xs truncate max-w-xs" style={{ color: "var(--color-text-secondary)" }}>{t.url}</p></td>
                  <td className="px-4 py-3 text-sm font-mono font-semibold" style={{ color: "var(--color-text)" }}>{t.current_price != null ? `$${t.current_price.toFixed(2)}` : "—"}</td>
                  <td className="px-4 py-3 text-sm font-mono" style={{ color: change ? (parseFloat(change) > 0 ? "#EF4444" : "#10B981") : "var(--color-text-secondary)" }}>{change ? `${parseFloat(change) > 0 ? "+" : ""}${change}%` : "—"}</td>
                  <td className="px-4 py-3 text-sm" style={{ color: "var(--color-text-secondary)" }}>{t.last_checked || "Never"}</td>
                  <td className="px-4 py-3"><span className="text-xs font-medium px-2.5 py-1 rounded-full" style={{ backgroundColor: t.status === "active" ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)", color: t.status === "active" ? "#10B981" : "#EF4444" }}>{t.status}</span></td>
                  <td className="px-4 py-3 text-right">
                    <button 
                      onClick={() => handleDelete(t.id)} 
                      className="text-xs font-medium px-3 py-1 rounded transition-colors"
                      style={{ backgroundColor: "rgba(239,68,68,0.1)", color: "#EF4444" }}
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
