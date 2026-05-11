"use client";
import { useState, useEffect } from "react";
import { apiClient, trackEvent } from "@devforge/core";

interface FeedbackEntry {
  id: number;
  text: string;
  sentiment: "positive" | "negative" | "neutral" | null;
  confidence: number | null;
  themes: string[] | null;
  is_urgent: boolean | null;
  draft_reply: string | null;
  analyzed_at: string | null;
  created_at: string;
  status: string;
}

const sentimentConfig = {
  positive: { label: "Positivo", color: "#10B981", bg: "rgba(16,185,129,0.12)" },
  negative: { label: "Negativo", color: "#EF4444", bg: "rgba(239,68,68,0.12)" },
  neutral:  { label: "Neutral",  color: "#A3A3A3", bg: "rgba(163,163,163,0.12)" },
};

export default function DashboardPage() {
  const [entries, setEntries]         = useState<FeedbackEntry[]>([]);
  const [text, setText]               = useState("");
  const [analyzing, setAnalyzing]     = useState<Set<number>>(new Set());
  const [selected, setSelected]       = useState<FeedbackEntry | null>(null);
  const [submitting, setSubmitting]   = useState(false);
  const [filter, setFilter]           = useState<"all" | "urgent" | "negative">("all");

  useEffect(() => {
    apiClient.get<FeedbackEntry[]>("/feedback/list").then(({ data }) => setEntries(data)).catch(() => {});
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    setSubmitting(true);
    trackEvent("feature_used", { feature_name: "add_feedback" });
    try {
      const { data } = await apiClient.post<FeedbackEntry>("/feedback", { text });
      setEntries(prev => [data, ...prev]);
      setText("");
      handleAnalyze(data.id);
    } catch { alert("Error al guardar feedback"); }
    finally { setSubmitting(false); }
  };

  const handleAnalyze = async (id: number) => {
    setAnalyzing(prev => new Set(prev).add(id));
    trackEvent("feature_used", { feature_name: "analyze_feedback" });
    try {
      const { data } = await apiClient.post<FeedbackEntry>(`/feedback/${id}/analyze`);
      setEntries(prev => prev.map(e => e.id === id ? data : e));
      if (selected?.id === id) setSelected(data);
    } catch { alert("Error al analizar"); }
    finally { setAnalyzing(prev => { const s = new Set(prev); s.delete(id); return s; }); }
  };

  const urgent   = entries.filter(e => e.is_urgent);
  const negative = entries.filter(e => e.sentiment === "negative");
  const positive = entries.filter(e => e.sentiment === "positive");

  const filtered = entries.filter(e => {
    if (filter === "urgent")   return e.is_urgent;
    if (filter === "negative") return e.sentiment === "negative";
    return true;
  });

  return (
    <div className="flex gap-6">
      <div className="flex-1 min-w-0">

        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "var(--color-text)" }}>Feedback Lens</h1>
            <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{entries.length} entradas analizadas</p>
          </div>
        </div>

        {urgent.length > 0 && (
          <div className="p-4 rounded-lg mb-6 flex items-start gap-3"
            style={{ backgroundColor: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)" }}>
            <div className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0 animate-pulse" style={{ backgroundColor: "#EF4444" }} />
            <div>
              <p className="text-sm font-bold" style={{ color: "#EF4444" }}>
                {urgent.length} feedback urgente{urgent.length > 1 ? "s" : ""} detectado{urgent.length > 1 ? "s" : ""}
              </p>
              <p className="text-xs mt-0.5" style={{ color: "var(--color-text-secondary)" }}>
                Estos mensajes requieren atencion inmediata — posibles errores criticos o quejas graves.
              </p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-3 gap-4 mb-6">
          {[
            { label: "Positivo",  value: positive.length, color: "#10B981" },
            { label: "Negativo",  value: negative.length, color: "#EF4444" },
            { label: "Urgente",   value: urgent.length,   color: "#F59E0B" },
          ].map(s => (
            <div key={s.label} className="p-4 rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
              <p className="text-xs mb-1" style={{ color: "var(--color-text-secondary)" }}>{s.label}</p>
              <p className="text-xl font-bold font-mono" style={{ color: s.color }}>{s.value}</p>
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="p-4 rounded-lg mb-6" style={{ backgroundColor: "var(--color-surface)" }}>
          <textarea value={text} onChange={e => setText(e.target.value)}
            className="input-field w-full h-24 mb-3 resize-none"
            placeholder="Pega aqui el feedback de un cliente, review o ticket..." />
          <button type="submit" disabled={submitting || !text.trim()} className="btn-primary w-full"
            style={{ opacity: submitting || !text.trim() ? 0.6 : 1 }}>
            {submitting ? "Guardando y analizando..." : "Analizar con IA"}
          </button>
        </form>

        <div className="flex gap-2 mb-4">
          {(["all", "urgent", "negative"] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className="text-xs font-medium px-4 py-2 rounded-md transition-colors"
              style={{
                backgroundColor: filter === f ? "var(--color-accent-dim)" : "var(--color-surface)",
                color: filter === f ? "var(--color-accent)" : "var(--color-text-secondary)",
              }}>
              {f === "all" ? `Todos (${entries.length})` : f === "urgent" ? `Urgentes (${urgent.length})` : `Negativos (${negative.length})`}
            </button>
          ))}
        </div>

        <div className="space-y-3">
          {filtered.length === 0 && (
            <div className="p-12 text-center rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
              <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
                {filter === "all" ? "Pega tu primer feedback arriba para comenzar." : "No hay entradas en esta categoria."}
              </p>
            </div>
          )}
          {filtered.map(entry => {
            const cfg = entry.sentiment ? sentimentConfig[entry.sentiment] : null;
            return (
              <div key={entry.id} onClick={() => setSelected(entry)}
                className="p-4 rounded-lg cursor-pointer transition-colors"
                style={{
                  backgroundColor: selected?.id === entry.id ? "var(--color-surface-raised)" : "var(--color-surface)",
                  border: entry.is_urgent ? "1px solid rgba(239,68,68,0.4)" : "1px solid transparent",
                }}>
                <div className="flex items-start justify-between gap-4">
                  <p className="text-sm line-clamp-2" style={{ color: "var(--color-text)" }}>{entry.text}</p>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {entry.is_urgent && (
                      <span className="text-xs font-bold px-2 py-0.5 rounded-full"
                        style={{ backgroundColor: "rgba(239,68,68,0.15)", color: "#EF4444" }}>URGENTE</span>
                    )}
                    {cfg && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full"
                        style={{ backgroundColor: cfg.bg, color: cfg.color }}>{cfg.label}</span>
                    )}
                    {!entry.analyzed_at && (
                      <button onClick={e => { e.stopPropagation(); handleAnalyze(entry.id); }}
                        disabled={analyzing.has(entry.id)}
                        className="text-xs px-2 py-1 rounded"
                        style={{ backgroundColor: "var(--color-surface-high)", color: "var(--color-text-secondary)" }}>
                        {analyzing.has(entry.id) ? "Analizando..." : "Analizar"}
                      </button>
                    )}
                  </div>
                </div>
                {entry.themes && entry.themes.length > 0 && (
                  <div className="flex gap-1 mt-2 flex-wrap">
                    {entry.themes.map(t => (
                      <span key={t} className="text-xs px-2 py-0.5 rounded"
                        style={{ backgroundColor: "var(--color-surface-high)", color: "var(--color-text-secondary)" }}>{t}</span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {selected && (
        <div className="w-80 flex-shrink-0 rounded-lg p-4 space-y-4" style={{ backgroundColor: "var(--color-surface)" }}>
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Detalle</p>
            <button onClick={() => setSelected(null)} className="text-xs" style={{ color: "var(--color-text-secondary)" }}>Cerrar</button>
          </div>
          <div className="p-3 rounded-lg" style={{ backgroundColor: "var(--color-bg)" }}>
            <p className="text-xs" style={{ color: "var(--color-text)" }}>{selected.text}</p>
          </div>
          {selected.sentiment && (() => {
            const cfg = sentimentConfig[selected.sentiment];
            return (
              <div className="grid grid-cols-2 gap-2">
                <div className="p-3 rounded-lg" style={{ backgroundColor: cfg.bg }}>
                  <p className="text-xs mb-0.5" style={{ color: "var(--color-text-secondary)" }}>Sentimiento</p>
                  <p className="text-sm font-bold" style={{ color: cfg.color }}>{cfg.label}</p>
                </div>
                <div className="p-3 rounded-lg" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                  <p className="text-xs mb-0.5" style={{ color: "var(--color-text-secondary)" }}>Confianza</p>
                  <p className="text-sm font-bold font-mono" style={{ color: "var(--color-text)" }}>{selected.confidence ? `${Math.round(selected.confidence * 100)}%` : "—"}</p>
                </div>
              </div>
            );
          })()}
          {selected.draft_reply && (
            <div>
              <p className="text-xs font-medium mb-2 uppercase tracking-wide" style={{ color: "var(--color-text-secondary)" }}>Borrador de respuesta</p>
              <div className="p-3 rounded-lg text-xs" style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text)" }}>
                {selected.draft_reply}
              </div>
              <button onClick={() => { navigator.clipboard.writeText(selected.draft_reply!); }}
                className="btn-secondary w-full mt-2 text-xs">
                Copiar borrador
              </button>
            </div>
          )}
          {!selected.analyzed_at && (
            <button onClick={() => handleAnalyze(selected.id)} disabled={analyzing.has(selected.id)}
              className="btn-primary w-full text-xs"
              style={{ opacity: analyzing.has(selected.id) ? 0.6 : 1 }}>
              {analyzing.has(selected.id) ? "Analizando..." : "Analizar con IA"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
