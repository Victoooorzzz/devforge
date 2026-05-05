"use client";
import { useState, useEffect } from "react";
import { apiClient, trackEvent } from "@devforge/core";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { ExternalLink, TrendingDown, TrendingUp, AlertCircle, Trash2, ChevronDown, ChevronUp } from "lucide-react";

interface TrackedUrl {
  id: number;
  url: string;
  label: string;
  current_price: number | null;
  previous_price: number | null;
  min_price: number | null;
  in_stock: boolean | null;
  last_checked: string | null;
  status: "active" | "error";
}

interface HistoryPoint {
  price: number | null;
  in_stock: boolean | null;
  recorded_at: string;
}

export default function DashboardPage() {
  const [trackers, setTrackers] = useState<TrackedUrl[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ url: "", label: "" });
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [history, setHistory] = useState<Record<number, HistoryPoint[]>>({});

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
    } catch (err: any) {
      alert("Error al eliminar producto");
    }
  };

  const toggleExpand = async (id: number) => {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(id);
    if (!history[id]) {
      try {
        const { data } = await apiClient.get<HistoryPoint[]>(`/trackers/${id}/history`);
        setHistory(prev => ({ ...prev, [id]: data }));
      } catch (err) {
        console.error("Failed to fetch history", err);
      }
    }
  };

  const getPriceChange = (curr: number | null, prev: number | null) => {
    if (!curr || !prev || prev === 0) return null;
    return ((curr - prev) / prev * 100).toFixed(1);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "var(--color-text)" }}>Price Trackers</h1>
          <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{trackers.length} URLs monitored</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2">
          <span>{showForm ? "Cancel" : "+ Add URL"}</span>
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleAdd} className="p-6 rounded-xl mb-8 grid grid-cols-1 md:grid-cols-3 gap-4 items-end animate-in fade-in slide-in-from-top-4 duration-300" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
          <div className="md:col-span-1">
            <label className="block text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-text-secondary)" }}>Label</label>
            <input value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} className="input-field" placeholder="e.g. Amazon Echo Dot" required />
          </div>
          <div className="md:col-span-1">
            <label className="block text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-text-secondary)" }}>Product URL</label>
            <input type="url" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} className="input-field" placeholder="https://amazon.com/..." required />
          </div>
          <button type="submit" className="btn-primary w-full">Track Now</button>
        </form>
      )}

      <div className="space-y-4">
        {trackers.map((t) => {
          const change = getPriceChange(t.current_price, t.previous_price);
          const isExpanded = expandedId === t.id;
          const isMinPrice = t.current_price != null && t.min_price != null && t.current_price <= t.min_price;

          return (
            <div key={t.id} className="rounded-xl overflow-hidden transition-all duration-200" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
              <div 
                className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer hover:bg-black/5"
                onClick={() => toggleExpand(t.id)}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-base font-semibold truncate" style={{ color: "var(--color-text)" }}>{t.label}</h3>
                    {t.in_stock === false && (
                      <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-red-500/10 text-red-500 border border-red-500/20">Out of Stock</span>
                    )}
                    {isMinPrice && (
                      <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 flex items-center gap-1">
                        <TrendingDown size={10} /> Min Price
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                    <a href={t.url} target="_blank" onClick={(e) => e.stopPropagation()} className="flex items-center gap-1 hover:text-[var(--color-primary)] transition-colors">
                      <ExternalLink size={12} /> View Product
                    </a>
                    <span>• Checked {t.last_checked ? new Date(t.last_checked).toLocaleTimeString() : "never"}</span>
                  </div>
                </div>

                <div className="flex items-center gap-8">
                  <div className="text-right">
                    <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: "var(--color-text-secondary)" }}>Current</p>
                    <p className="text-lg font-mono font-bold" style={{ color: "var(--color-text)" }}>
                      {t.current_price != null ? `$${t.current_price.toFixed(2)}` : "???"}
                    </p>
                  </div>

                  <div className="text-right hidden sm:block">
                    <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: "var(--color-text-secondary)" }}>Change</p>
                    <div className="flex items-center justify-end gap-1 font-mono font-bold" style={{ color: change ? (parseFloat(change) > 0 ? "#EF4444" : "#10B981") : "var(--color-text-secondary)" }}>
                      {change ? (
                        <>
                          {parseFloat(change) > 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                          <span>{parseFloat(change) > 0 ? "+" : ""}{change}%</span>
                        </>
                      ) : "—"}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleDelete(t.id); }}
                      className="p-2 rounded-lg hover:bg-red-500/10 text-red-500/60 hover:text-red-500 transition-colors"
                    >
                      <Trash2 size={18} />
                    </button>
                    {isExpanded ? <ChevronUp size={20} style={{ color: "var(--color-text-secondary)" }} /> : <ChevronDown size={20} style={{ color: "var(--color-text-secondary)" }} />}
                  </div>
                </div>
              </div>

              {isExpanded && (
                <div className="p-6 border-t border-[var(--color-border)] animate-in fade-in slide-in-from-top-2 duration-300">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                    <div className="p-4 rounded-lg bg-black/5">
                      <p className="text-[10px] font-bold uppercase tracking-wider mb-1 opacity-50">Min Historical</p>
                      <p className="text-xl font-mono font-bold text-emerald-500">${t.min_price?.toFixed(2) || "—"}</p>
                    </div>
                    <div className="p-4 rounded-lg bg-black/5">
                      <p className="text-[10px] font-bold uppercase tracking-wider mb-1 opacity-50">Stock Status</p>
                      <p className={`text-xl font-bold ${t.in_stock ? "text-emerald-500" : "text-red-500"}`}>
                        {t.in_stock === null ? "Unknown" : t.in_stock ? "In Stock" : "Out of Stock"}
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-black/5">
                      <p className="text-[10px] font-bold uppercase tracking-wider mb-1 opacity-50">Last Price</p>
                      <p className="text-xl font-mono font-bold">${t.previous_price?.toFixed(2) || "—"}</p>
                    </div>
                    <div className="p-4 rounded-lg bg-black/5">
                      <p className="text-[10px] font-bold uppercase tracking-wider mb-1 opacity-50">Tracker Status</p>
                      <p className="text-xl font-bold text-[var(--color-primary)] capitalize">{t.status}</p>
                    </div>
                  </div>

                  <div className="h-[250px] w-full mt-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider mb-4 opacity-50">Price History (Last 30 Checks)</h4>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={history[t.id] || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                        <XAxis 
                          dataKey="recorded_at" 
                          hide 
                        />
                        <YAxis 
                          domain={['auto', 'auto']} 
                          fontSize={10} 
                          tickFormatter={(val) => `$${val}`}
                          stroke="rgba(255,255,255,0.3)"
                        />
                        <Tooltip 
                          contentStyle={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "8px", fontSize: "12px" }}
                          itemStyle={{ color: "var(--color-primary)" }}
                          labelFormatter={(label) => new Date(label).toLocaleString()}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="price" 
                          stroke="var(--color-primary)" 
                          strokeWidth={2} 
                          dot={{ r: 3, fill: "var(--color-primary)" }} 
                          activeDot={{ r: 5 }} 
                          animationDuration={1000}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </div>
          );
        })}
        {trackers.length === 0 && (
          <div className="text-center py-20 rounded-xl border-2 border-dashed border-[var(--color-border)]">
            <AlertCircle size={48} className="mx-auto mb-4 opacity-20" />
            <h3 className="text-lg font-medium opacity-50">No URLs being tracked yet</h3>
            <button onClick={() => setShowForm(true)} className="mt-4 text-[var(--color-primary)] font-semibold hover:underline">Add your first URL</button>
          </div>
        )}
      </div>
    </div>
  );
}

