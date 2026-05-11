"use client";
import { useState, useEffect } from "react";
import { apiClient, trackEvent } from "@devforge/core";

interface TrackedUrl {
  id: number;
  url: string;
  label: string;
  current_price: number | null;
  previous_price: number | null;
  min_price: number | null;
  in_stock: boolean | null;
  last_checked: string | null;
  check_frequency_hours: number;
  status: string;
}

interface PricePoint {
  price: number | null;
  in_stock: boolean | null;
  recorded_at: string;
}

export default function DashboardPage() {
  const [trackers, setTrackers]   = useState<TrackedUrl[]>([]);
  const [showForm, setShowForm]   = useState(false);
  const [selected, setSelected]  = useState<TrackedUrl | null>(null);
  const [history, setHistory]     = useState<PricePoint[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [deleting, setDeleting]   = useState<Set<number>>(new Set());
  const [form, setForm]           = useState({ url: "", label: "" });

  useEffect(() => {
    apiClient.get<TrackedUrl[]>("/trackers/list").then(({ data }) => setTrackers(data)).catch(() => {});
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    trackEvent("feature_used", { feature_name: "add_tracker" });
    const { data } = await apiClient.post<TrackedUrl>("/trackers", { url: form.url, label: form.label });
    setTrackers(prev => [data, ...prev]);
    setForm({ url: "", label: "" });
    setShowForm(false);
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Dejar de rastrear este producto?")) return;
    setDeleting(prev => new Set(prev).add(id));
    try {
      await apiClient.delete(`/trackers/${id}`);
      setTrackers(prev => prev.filter(t => t.id !== id));
      if (selected?.id === id) setSelected(null);
    } catch { alert("Error al eliminar"); }
    finally { setDeleting(prev => { const s = new Set(prev); s.delete(id); return s; }); }
  };

  const handleSelect = async (t: TrackedUrl) => {
    setSelected(t);
    setLoadingHistory(true);
    trackEvent("feature_used", { feature_name: "view_price_history" });
    try {
      const { data } = await apiClient.get<PricePoint[]>(`/trackers/${t.id}/history`);
      setHistory(data);
    } catch { setHistory([]); }
    finally { setLoadingHistory(false); }
  };

  const priceDiff = (t: TrackedUrl) => {
    if (!t.current_price || !t.previous_price) return null;
    return ((t.current_price - t.previous_price) / t.previous_price) * 100;
  };

  const isMinHistoric = (t: TrackedUrl) =>
    t.current_price !== null && t.min_price !== null && t.current_price <= t.min_price;

  // Mini sparkline SVG desde array de precios
  const Sparkline = ({ points }: { points: PricePoint[] }) => {
    const prices = points.map(p => p.price).filter(Boolean) as number[];
    if (prices.length < 2) return <span className="text-xs" style={{ color: "var(--color-text-secondary)" }}>Sin datos</span>;
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || 1;
    const w = 120; const h = 32;
    const pts = prices.map((p, i) => `${(i / (prices.length - 1)) * w},${h - ((p - min) / range) * h}`).join(" ");
    return (
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
        <polyline fill="none" stroke="var(--color-accent)" strokeWidth="1.5" points={pts} />
      </svg>
    );
  };

  return (
    <div className="flex gap-6">
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "var(--color-text)" }}>Price Tracker</h1>
            <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{trackers.length} productos rastreados</p>
          </div>
          <button onClick={() => setShowForm(!showForm)} className="btn-primary">+ Agregar URL</button>
        </div>

        {showForm && (
          <form onSubmit={handleAdd} className="p-6 rounded-lg mb-6 grid grid-cols-1 md:grid-cols-3 gap-4 items-end"
            style={{ backgroundColor: "var(--color-surface)" }}>
            <div className="md:col-span-1">
              <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>Nombre del producto</label>
              <input value={form.label} onChange={e => setForm({ ...form, label: e.target.value })} className="input-field" placeholder="Ej: iPhone 15 Pro" required />
            </div>
            <div className="md:col-span-1">
              <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--color-text-secondary)" }}>URL del producto</label>
              <input type="url" value={form.url} onChange={e => setForm({ ...form, url: e.target.value })} className="input-field" placeholder="https://..." required />
            </div>
            <button type="submit" className="btn-primary">Guardar</button>
          </form>
        )}

        <div className="space-y-3">
          {trackers.length === 0 && (
            <div className="p-12 text-center rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
              <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
                Aun no rastreas ningun producto. Agrega una URL para empezar.
              </p>
            </div>
          )}
          {trackers.map(t => {
            const diff = priceDiff(t);
            const isMin = isMinHistoric(t);
            return (
              <div key={t.id} onClick={() => handleSelect(t)} className="p-4 rounded-lg cursor-pointer transition-colors"
                style={{
                  backgroundColor: selected?.id === t.id ? "var(--color-surface-raised)" : "var(--color-surface)",
                  border: isMin ? "1px solid rgba(16,185,129,0.4)" : "1px solid transparent",
                }}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-sm font-semibold truncate" style={{ color: "var(--color-text)" }}>{t.label}</p>
                      {isMin && (
                        <span className="text-xs font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: "rgba(16,185,129,0.15)", color: "#10B981" }}>
                          MINIMO HISTORICO
                        </span>
                      )}
                      {t.in_stock === false && (
                        <span className="text-xs font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: "rgba(239,68,68,0.15)", color: "#EF4444" }}>
                          SIN STOCK
                        </span>
                      )}
                    </div>
                    <p className="text-xs truncate" style={{ color: "var(--color-text-secondary)" }}>{t.url}</p>
                  </div>
                  <div className="flex items-center gap-4 flex-shrink-0">
                    <div className="text-right">
                      {t.current_price !== null ? (
                        <p className="text-lg font-bold font-mono" style={{ color: "var(--color-accent)" }}>
                          ${t.current_price.toFixed(2)}
                        </p>
                      ) : (
                        <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>Sin precio</p>
                      )}
                      {diff !== null && (
                        <p className="text-xs font-mono" style={{ color: diff < 0 ? "#10B981" : "#EF4444" }}>
                          {diff < 0 ? "▼" : "▲"} {Math.abs(diff).toFixed(1)}%
                        </p>
                      )}
                    </div>
                    <button onClick={e => { e.stopPropagation(); handleDelete(t.id); }}
                      disabled={deleting.has(t.id)}
                      className="text-xs px-2 py-1 rounded transition-colors"
                      style={{ backgroundColor: "var(--color-surface-high)", color: "var(--color-text-secondary)" }}>
                      {deleting.has(t.id) ? "..." : "Eliminar"}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {selected && (
        <div className="w-80 flex-shrink-0 rounded-lg p-4" style={{ backgroundColor: "var(--color-surface)" }}>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold truncate" style={{ color: "var(--color-text)" }}>{selected.label}</p>
            <button onClick={() => setSelected(null)} className="text-xs" style={{ color: "var(--color-text-secondary)" }}>Cerrar</button>
          </div>
          {loadingHistory ? (
            <p className="text-xs text-center py-8" style={{ color: "var(--color-text-secondary)" }}>Cargando historial...</p>
          ) : history.length === 0 ? (
            <p className="text-xs text-center py-8" style={{ color: "var(--color-text-secondary)" }}>Sin historial aun. El primer check se realiza en las proximas horas.</p>
          ) : (
            <div className="space-y-4">
              <div>
                <p className="text-xs font-medium mb-2 uppercase tracking-wide" style={{ color: "var(--color-text-secondary)" }}>Fluctuacion de precio</p>
                <Sparkline points={history} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Precio min", value: selected.min_price ? `$${selected.min_price.toFixed(2)}` : "—", color: "#10B981" },
                  { label: "Precio actual", value: selected.current_price ? `$${selected.current_price.toFixed(2)}` : "—", color: "var(--color-accent)" },
                ].map(s => (
                  <div key={s.label} className="p-3 rounded-lg" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                    <p className="text-xs mb-1" style={{ color: "var(--color-text-secondary)" }}>{s.label}</p>
                    <p className="text-base font-bold font-mono" style={{ color: s.color }}>{s.value}</p>
                  </div>
                ))}
              </div>
              <div>
                <p className="text-xs font-medium mb-2 uppercase tracking-wide" style={{ color: "var(--color-text-secondary)" }}>Ultimos registros</p>
                <div className="space-y-1 max-h-48 overflow-auto">
                  {history.slice(0, 20).map((p, i) => (
                    <div key={i} className="flex justify-between text-xs py-1" style={{ borderBottom: "1px solid rgba(38,38,38,0.3)" }}>
                      <span style={{ color: "var(--color-text-secondary)" }}>{new Date(p.recorded_at).toLocaleDateString("es-PE")}</span>
                      <span className="font-mono" style={{ color: "var(--color-text)" }}>{p.price ? `$${p.price.toFixed(2)}` : "—"}</span>
                      <span style={{ color: p.in_stock ? "#10B981" : "#EF4444" }}>{p.in_stock === null ? "—" : p.in_stock ? "Stock" : "Agotado"}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
