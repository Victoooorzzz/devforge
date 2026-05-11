"use client";
import { useState, useEffect, useRef } from "react";
import { apiClient, trackEvent } from "@devforge/core";
import { Download, ChevronDown, Bell, BellOff, Send, Loader2, X, Check } from "lucide-react";

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

type ExportFormat = "csv" | "xlsx" | "json";

interface AlertConfig {
  threshold: string;
  open: boolean;
  saving: boolean;
  testing: boolean;
  saved: boolean;
}

export default function DashboardPage() {
  const [trackers, setTrackers]   = useState<TrackedUrl[]>([]);
  const [showForm, setShowForm]   = useState(false);
  const [selected, setSelected]  = useState<TrackedUrl | null>(null);
  const [history, setHistory]     = useState<PricePoint[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [deleting, setDeleting]   = useState<Set<number>>(new Set());
  const [form, setForm]           = useState({ url: "", label: "" });
  const [exportOpen, setExportOpen] = useState(false);
  const [alertConfigs, setAlertConfigs] = useState<Record<number, AlertConfig>>({});
  const exportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiClient.get<TrackedUrl[]>("/trackers/list").then(({ data }) => setTrackers(data)).catch(() => {});
  }, []);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) setExportOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
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

  // Export — Skill: react-patterns
  const handleExport = async (format: ExportFormat) => {
    setExportOpen(false);
    trackEvent("feature_used", { feature_name: "export_trackers", format });
    const token = typeof window !== "undefined" ? localStorage.getItem("devforge_token") : null;
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}/trackers/export?format=${format}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) { alert("Error al exportar"); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `pricetrackr_export.${format}`; a.click();
    URL.revokeObjectURL(url);
  };

  // Alert threshold config — Skill: backend-architect
  const toggleAlertPanel = (id: number) => {
    setAlertConfigs(prev => ({
      ...prev,
      [id]: prev[id]?.open 
        ? { ...prev[id], open: false }
        : { threshold: "", open: true, saving: false, testing: false, saved: false }
    }));
  };

  const handleSaveAlert = async (id: number) => {
    const cfg = alertConfigs[id];
    if (!cfg?.threshold) return;
    setAlertConfigs(prev => ({ ...prev, [id]: { ...prev[id], saving: true, saved: false } }));
    trackEvent("feature_used", { feature_name: "set_price_alert" });
    try {
      await apiClient.patch(`/trackers/${id}/alert-threshold`, {
        alert_threshold: parseFloat(cfg.threshold)
      });
      setAlertConfigs(prev => ({ ...prev, [id]: { ...prev[id], saving: false, saved: true, open: false } }));
      setTimeout(() => setAlertConfigs(prev => ({ ...prev, [id]: { ...prev[id], saved: false } })), 3000);
    } catch {
      setAlertConfigs(prev => ({ ...prev, [id]: { ...prev[id], saving: false } }));
      alert("Error al guardar alerta");
    }
  };

  const handleTestAlert = async (id: number) => {
    setAlertConfigs(prev => ({ ...prev, [id]: { ...(prev[id] || { threshold: "", open: false, saving: false, saved: false }), testing: true } }));
    trackEvent("feature_used", { feature_name: "test_price_alert" });
    try {
      await apiClient.post(`/trackers/${id}/test-alert`, {});
      alert("📧 Email de prueba enviado exitosamente!");
    } catch { alert("Error al enviar test alert"); }
    finally { setAlertConfigs(prev => ({ ...prev, [id]: { ...prev[id], testing: false } })); }
  };

  const priceDiff = (t: TrackedUrl) => {
    if (!t.current_price || !t.previous_price) return null;
    return ((t.current_price - t.previous_price) / t.previous_price) * 100;
  };

  const isMinHistoric = (t: TrackedUrl) =>
    t.current_price !== null && t.min_price !== null && t.current_price <= t.min_price;

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
          <div className="flex items-center gap-2">
            {/* Export dropdown */}
            <div className="relative" ref={exportRef}>
              <button onClick={() => setExportOpen(!exportOpen)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all"
                style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)" }}>
                <Download size={14} />
                <span>Export</span>
                <ChevronDown size={12} className={`transition-transform ${exportOpen ? "rotate-180" : ""}`} />
              </button>
              {exportOpen && (
                <div className="absolute right-0 top-full mt-2 w-44 rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200"
                  style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                  {(["csv", "xlsx", "json"] as ExportFormat[]).map(f => (
                    <button key={f} onClick={() => handleExport(f)}
                      className="w-full text-left px-4 py-2.5 text-sm hover:bg-black/5 transition-colors"
                      style={{ color: "var(--color-text)" }}>
                      {f.toUpperCase()} — {f === "csv" ? "Spreadsheet" : f === "xlsx" ? "Excel" : "JSON"}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button onClick={() => setShowForm(!showForm)} className="btn-primary">+ Agregar URL</button>
          </div>
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
            const alertCfg = alertConfigs[t.id];
            return (
              <div key={t.id} className="rounded-lg overflow-hidden" style={{ backgroundColor: selected?.id === t.id ? "var(--color-surface-raised)" : "var(--color-surface)", border: isMin ? "1px solid rgba(16,185,129,0.4)" : "1px solid transparent" }}>
                <div onClick={() => handleSelect(t)} className="p-4 flex items-start justify-between gap-4 cursor-pointer">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-sm font-semibold truncate" style={{ color: "var(--color-text)" }}>{t.label}</p>
                      {isMin && (
                        <span className="text-xs font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: "rgba(16,185,129,0.15)", color: "#10B981" }}>MINIMO</span>
                      )}
                      {t.in_stock === false && (
                        <span className="text-xs font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: "rgba(239,68,68,0.15)", color: "#EF4444" }}>SIN STOCK</span>
                      )}
                      {/* Alert configured badge */}
                      {alertCfg?.saved && (
                        <span className="text-xs font-bold px-2 py-0.5 rounded-full flex-shrink-0 animate-in fade-in"
                          style={{ backgroundColor: "rgba(99,102,241,0.15)", color: "#6366F1" }}>
                          <Bell size={10} className="inline mr-1" />ALERTA ACTIVA
                        </span>
                      )}
                    </div>
                    <p className="text-xs truncate" style={{ color: "var(--color-text-secondary)" }}>{t.url}</p>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
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
                    {/* Alert button */}
                    <button
                      onClick={e => { e.stopPropagation(); toggleAlertPanel(t.id); }}
                      className="p-2 rounded-lg transition-colors"
                      style={{
                        backgroundColor: alertCfg?.open ? "rgba(99,102,241,0.1)" : "var(--color-surface-high)",
                        color: alertCfg?.open ? "#6366F1" : "var(--color-text-secondary)"
                      }}
                      title="Configurar alerta de precio"
                    >
                      {alertCfg?.saved ? <Bell size={16} /> : <BellOff size={16} />}
                    </button>
                    <button onClick={e => { e.stopPropagation(); handleDelete(t.id); }}
                      disabled={deleting.has(t.id)}
                      className="text-xs px-2 py-1 rounded transition-colors"
                      style={{ backgroundColor: "var(--color-surface-high)", color: "var(--color-text-secondary)" }}>
                      {deleting.has(t.id) ? "..." : "Eliminar"}
                    </button>
                  </div>
                </div>

                {/* Alert configuration panel */}
                {alertCfg?.open && (
                  <div className="px-4 pb-4 border-t border-[var(--color-border)] pt-3 animate-in fade-in slide-in-from-top-2 duration-200">
                    <p className="text-xs font-medium mb-2 flex items-center gap-1.5"
                      style={{ color: "var(--color-text-secondary)" }}>
                      <Bell size={12} /> Alerta cuando el precio baje de:
                    </p>
                    <div className="flex items-center gap-2">
                      <div className="relative flex-1">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-mono"
                          style={{ color: "var(--color-text-secondary)" }}>$</span>
                        <input
                          type="number" step="0.01" min="0"
                          value={alertCfg.threshold}
                          onChange={e => setAlertConfigs(prev => ({ ...prev, [t.id]: { ...prev[t.id], threshold: e.target.value } }))}
                          className="input-field pl-7 text-sm"
                          placeholder={t.current_price ? (t.current_price * 0.9).toFixed(2) : "0.00"}
                        />
                      </div>
                      <button onClick={() => handleSaveAlert(t.id)}
                        disabled={alertCfg.saving || !alertCfg.threshold}
                        className="px-3 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-1.5"
                        style={{ backgroundColor: "var(--color-primary)", color: "#000", opacity: alertCfg.saving || !alertCfg.threshold ? 0.6 : 1 }}>
                        {alertCfg.saving ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
                        Guardar
                      </button>
                      <button onClick={() => handleTestAlert(t.id)}
                        disabled={alertCfg.testing}
                        className="px-3 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-1.5"
                        style={{ backgroundColor: "var(--color-surface-high)", color: "var(--color-text)" }}>
                        {alertCfg.testing ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                        Test
                      </button>
                      <button onClick={() => toggleAlertPanel(t.id)}
                        className="p-2 rounded-lg hover:bg-black/5 transition-colors"
                        style={{ color: "var(--color-text-secondary)" }}>
                        <X size={14} />
                      </button>
                    </div>
                    <p className="text-[10px] mt-2" style={{ color: "var(--color-text-secondary)" }}>
                      Se enviará un email a tu cuenta cuando el precio detectado sea menor al umbral configurado.
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* History sidebar */}
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
