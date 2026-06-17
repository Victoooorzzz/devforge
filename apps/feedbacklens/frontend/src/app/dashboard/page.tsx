"use client";
import { useState, useEffect, useRef } from "react";
import { apiClient, downloadFile, trackEvent, uploadFile } from "@devforge/core";
import { 
  Sparkles, MessageSquare, Download, Upload, ChevronDown,
  Copy, Check, X, FileText, AlertCircle, Loader2
} from "lucide-react";

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

type Tab = "single" | "bulk";
type ExportFormat = "csv" | "xlsx" | "json";

export default function DashboardPage() {
  const [entries, setEntries]         = useState<FeedbackEntry[]>([]);
  const [text, setText]               = useState("");
  const [analyzing, setAnalyzing]     = useState<Set<number>>(new Set());
  const [draftingIds, setDraftingIds] = useState<Set<number>>(new Set());
  const [selected, setSelected]       = useState<FeedbackEntry | null>(null);
  const [submitting, setSubmitting]   = useState(false);
  const [filter, setFilter]           = useState<"all" | "urgent" | "negative">("all");
  const [tab, setTab]                 = useState<Tab>("single");
  const [bulkText, setBulkText]       = useState("");
  const [bulkImporting, setBulkImporting] = useState(false);
  const [bulkResult, setBulkResult]   = useState<{created: number} | null>(null);
  const [exportOpen, setExportOpen]   = useState(false);
  const [copiedReply, setCopiedReply] = useState<number | null>(null);
  const exportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiClient.get<FeedbackEntry[]>("/feedback/list").then(({ data }) => setEntries(data)).catch(() => {});
  }, []);

  // Close export dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) setExportOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
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

  // Draft Reply Generator — Skill: gemini-api-dev
  const handleDraftReply = async (id: number) => {
    setDraftingIds(prev => new Set(prev).add(id));
    trackEvent("feature_used", { feature_name: "draft_reply" });
    try {
      const { data } = await apiClient.post<FeedbackEntry>(`/feedback/${id}/draft-reply`);
      setEntries(prev => prev.map(e => e.id === id ? data : e));
      if (selected?.id === id) setSelected(data);
    } catch { alert("Error al generar borrador"); }
    finally { setDraftingIds(prev => { const s = new Set(prev); s.delete(id); return s; }); }
  };

  const handleCopyReply = (id: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedReply(id);
    setTimeout(() => setCopiedReply(null), 2000);
  };

  // Bulk Import — Skill: react-patterns
  const handleBulkImport = async () => {
    const texts = bulkText.split("\n").map(t => t.trim()).filter(Boolean);
    if (!texts.length) return;
    setBulkImporting(true);
    trackEvent("feature_used", { feature_name: "bulk_import_feedback" });
    try {
      const { data } = await apiClient.post<{created: number}>("/feedback/bulk", { texts });
      setBulkResult(data);
      setBulkText("");
      // Reload entries
      const { data: newEntries } = await apiClient.get<FeedbackEntry[]>("/feedback/list");
      setEntries(newEntries);
    } catch { alert("Error al importar"); }
    finally { setBulkImporting(false); }
  };

  const handleBulkCsvUpload = async (file: File) => {
    setBulkImporting(true);
    trackEvent("feature_used", { feature_name: "bulk_import_csv" });
    const formData = new FormData();
    formData.append("file", file);
    try {
      const { data } = await uploadFile<{ created: number }>("/feedback/bulk-csv", formData);
      setBulkResult({ created: data.created });
      const { data: newEntries } = await apiClient.get<FeedbackEntry[]>("/feedback/list");
      setEntries(newEntries);
    } catch { alert("Error al cargar CSV"); }
    finally { setBulkImporting(false); }
  };

  // Export — Skill: react-patterns
  const handleExport = async (format: ExportFormat) => {
    setExportOpen(false);
    trackEvent("feature_used", { feature_name: "export_feedback", format });
    try {
      await downloadFile(`/feedback/export?format=${format}`, `feedbacklens_export.${format}`);
    } catch {
      alert("Error al exportar");
    }
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
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "var(--color-text)" }}>Feedback Lens</h1>
            <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{entries.length} entradas analizadas</p>
          </div>
          {/* Export Dropdown */}
          <div className="relative" ref={exportRef}>
            <button
              onClick={() => setExportOpen(!exportOpen)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all"
              style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)" }}
            >
              <Download size={15} />
              <span>Exportar</span>
              <ChevronDown size={14} className={`transition-transform ${exportOpen ? "rotate-180" : ""}`} />
            </button>
            {exportOpen && (
              <div className="absolute right-0 top-full mt-2 w-44 rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200"
                style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                {(["csv", "xlsx", "json"] as ExportFormat[]).map(f => (
                  <button key={f} onClick={() => handleExport(f)}
                    className="w-full text-left px-4 py-2.5 text-sm hover:bg-black/5 transition-colors"
                    style={{ color: "var(--color-text)" }}>
                    {f.toUpperCase()} — {f === "csv" ? "Spreadsheet" : f === "xlsx" ? "Excel" : "JSON API"}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Urgent alert */}
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

        {/* Stats */}
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

        {/* Input Tabs — Single vs Bulk */}
        <div className="mb-4 flex gap-2">
          {(["single", "bulk"] as Tab[]).map(t => (
            <button key={t} onClick={() => { setTab(t); setBulkResult(null); }}
              className="text-xs font-medium px-4 py-2 rounded-md transition-colors flex items-center gap-1.5"
              style={{
                backgroundColor: tab === t ? "var(--color-accent-dim)" : "var(--color-surface)",
                color: tab === t ? "var(--color-accent)" : "var(--color-text-secondary)",
              }}>
              {t === "single" ? <><MessageSquare size={12} /> Individual</> : <><Upload size={12} /> Bulk import</>}
            </button>
          ))}
        </div>

        {/* Single feedback form */}
        {tab === "single" && (
          <form onSubmit={handleSubmit} className="p-4 rounded-lg mb-6" style={{ backgroundColor: "var(--color-surface)" }}>
            <textarea value={text} onChange={e => setText(e.target.value)}
              className="input-field w-full h-24 mb-3 resize-none"
              placeholder="Pega aqui el feedback de un cliente, review o ticket..." />
            <button type="submit" disabled={submitting || !text.trim()} className="btn-primary w-full"
              style={{ opacity: submitting || !text.trim() ? 0.6 : 1 }}>
              {submitting ? "Guardando y analizando..." : "Analizar con IA"}
            </button>
          </form>
        )}

        {/* Bulk Import */}
        {tab === "bulk" && (
          <div className="p-4 rounded-lg mb-6 space-y-3" style={{ backgroundColor: "var(--color-surface)" }}>
            <p className="text-xs font-medium" style={{ color: "var(--color-text-secondary)" }}>
              Un feedback por línea, o sube un CSV con columna <code className="bg-black/10 px-1 rounded">text</code>
            </p>
            <textarea value={bulkText} onChange={e => setBulkText(e.target.value)}
              className="input-field w-full h-32 resize-none font-mono text-xs"
              placeholder={"Feedback 1 del cliente...\nFeedback 2 del cliente...\nFeedback 3..."} />
            <div className="flex items-center gap-3">
              <button onClick={handleBulkImport} disabled={bulkImporting || !bulkText.trim()}
                className="btn-primary flex-1 flex items-center justify-center gap-2"
                style={{ opacity: bulkImporting || !bulkText.trim() ? 0.6 : 1 }}>
                {bulkImporting ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                {bulkImporting ? "Importando..." : `Importar ${bulkText.split("\n").filter(Boolean).length} entradas`}
              </button>
              <label className="px-4 py-2 rounded-lg text-sm font-medium cursor-pointer transition-colors flex items-center gap-2"
                style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text)" }}>
                <FileText size={14} />
                Subir CSV
                <input type="file" accept=".csv" className="hidden" onChange={e => {
                  const f = e.target.files?.[0];
                  if (f) handleBulkCsvUpload(f);
                }} />
              </label>
            </div>
            {bulkResult && (
              <div className="flex items-center gap-2 p-3 rounded-lg animate-in fade-in"
                style={{ backgroundColor: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.3)" }}>
                <Check size={14} className="text-emerald-500" />
                <p className="text-sm font-medium text-emerald-500">{bulkResult.created} entradas importadas exitosamente</p>
              </div>
            )}
          </div>
        )}

        {/* Filter tabs */}
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

        {/* Entry list */}
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
            const isDrafting = draftingIds.has(entry.id);
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
                    {/* Draft Reply button — Skill: gemini-api-dev */}
                    {entry.analyzed_at && !entry.draft_reply && (
                      <button onClick={e => { e.stopPropagation(); handleDraftReply(entry.id); }}
                        disabled={isDrafting}
                        className="text-xs px-2 py-1 rounded flex items-center gap-1 transition-colors"
                        style={{ backgroundColor: "rgba(99,102,241,0.1)", color: "#6366F1" }}>
                        {isDrafting ? <Loader2 size={10} className="animate-spin" /> : <Sparkles size={10} />}
                        {isDrafting ? "Generando..." : "Draft"}
                      </button>
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

      {/* Detail panel */}
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
                  <p className="text-sm font-bold font-mono" style={{ color: "var(--color-text)" }}>
                    {selected.confidence ? `${Math.round(selected.confidence * 100)}%` : "—"}
                  </p>
                </div>
              </div>
            );
          })()}

          {/* Draft Reply section */}
          {selected.draft_reply ? (
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--color-text-secondary)" }}>
                  Borrador de respuesta
                </p>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400">AI</span>
              </div>
              <div className="p-3 rounded-lg text-xs" style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text)" }}>
                {selected.draft_reply}
              </div>
              <button onClick={() => handleCopyReply(selected.id, selected.draft_reply!)}
                className="btn-secondary w-full mt-2 text-xs flex items-center justify-center gap-1.5">
                {copiedReply === selected.id ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                {copiedReply === selected.id ? "Copiado!" : "Copiar borrador"}
              </button>
              <button onClick={() => handleDraftReply(selected.id)} disabled={draftingIds.has(selected.id)}
                className="w-full mt-1 text-xs py-1.5 rounded-lg transition-colors flex items-center justify-center gap-1.5"
                style={{ color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>
                {draftingIds.has(selected.id) ? <Loader2 size={10} className="animate-spin" /> : <Sparkles size={10} />}
                Regenerar
              </button>
            </div>
          ) : selected.analyzed_at ? (
            <button onClick={() => handleDraftReply(selected.id)} disabled={draftingIds.has(selected.id)}
              className="btn-primary w-full text-xs flex items-center justify-center gap-2"
              style={{ opacity: draftingIds.has(selected.id) ? 0.6 : 1 }}>
              {draftingIds.has(selected.id) ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              {draftingIds.has(selected.id) ? "Generando con IA..." : "Generar Draft Reply"}
            </button>
          ) : (
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
