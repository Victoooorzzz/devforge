"use client";
import { useState, useRef } from "react";
import Link from "next/link";

interface CleanResult {
  rows_before: number;
  rows_after: number;
  duplicates_removed: number;
  nulls_removed: number;
  columns_normalized: number;
  download_url: string;
  file_name: string;
}

export default function DemoPage() {
  const [file, setFile]           = useState<File | null>(null);
  const [loading, setLoading]     = useState(false);
  const [result, setResult]       = useState<CleanResult | null>(null);
  const [error, setError]         = useState("");
  const [dragOver, setDragOver]   = useState(false);
  const inputRef                  = useRef<HTMLInputElement>(null);

  const handleFile = (f: File) => {
    const allowed = [".csv", ".xlsx", ".xls"];
    const ext = "." + f.name.split(".").pop()?.toLowerCase();
    if (!allowed.includes(ext)) {
      setError("Solo se aceptan archivos CSV y Excel (.csv, .xlsx, .xls)");
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      setError("El archivo supera el limite de 50MB");
      return;
    }
    setFile(f);
    setError("");
    setResult(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const handleClean = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

      const uploadRes = await fetch(`${apiUrl}/files/demo/upload`, {
        method: "POST",
        body: formData,
      });
      if (!uploadRes.ok) {
        const data = await uploadRes.json();
        throw new Error(data.detail || "Error al subir el archivo");
      }
      const uploadData = await uploadRes.json();
      const fileId = uploadData.id;

      // Poll status until completed, failed or canceled
      let status = "pending";
      let statusData: any = null;
      while (status === "pending" || status === "queued" || status === "processing") {
        await new Promise(resolve => setTimeout(resolve, 2000));
        const statusRes = await fetch(`${apiUrl}/files/demo/${fileId}/status`);
        if (!statusRes.ok) {
          throw new Error("Error al obtener estado de procesamiento");
        }
        statusData = await statusRes.json();
        status = statusData.status;
      }

      if (status === "failed" || status === "error") {
        throw new Error(statusData?.error || "Error al procesar el archivo");
      }

      // Fetch the execution report
      const reportRes = await fetch(`${apiUrl}/files/demo/${fileId}/report`);
      if (!reportRes.ok) {
        throw new Error("Error al obtener reporte de limpieza");
      }
      const reportData = await reportRes.json();

      setResult({
        rows_before:          reportData.rows_original          ?? 0,
        rows_after:           reportData.rows_clean           ?? 0,
        duplicates_removed:   reportData.duplicates_removed   ?? 0,
        nulls_removed:        reportData.empty_removed        ?? 0,
        columns_normalized:   ((reportData.normalization?.countries_normalized ?? 0) +
                               (reportData.normalization?.phones_normalized ?? 0) +
                               (reportData.normalization?.currencies_normalized ?? 0) +
                               (reportData.normalization?.dates_normalized ?? 0)),
        download_url:         `${apiUrl}/files/demo/${fileId}/download`,
        file_name:            uploadData.name            ?? file.name,
      });
    } catch (err: any) {
      setError(err.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!result) return;
    const a = document.createElement("a");
    a.href = result.download_url;
    a.download = `cleaned_${result.file_name}`;
    a.click();
  };

  return (
    <div className="min-h-screen bg-black text-white">
      <nav className="fixed top-0 w-full z-50 glass border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-sm" style={{ color: "var(--color-text-secondary)" }}>
            ← Back
          </Link>
          <span className="text-sm font-bold" style={{ color: "var(--color-text)" }}>
            File<span style={{ color: "var(--color-accent)" }}>Cleaner</span> — Demo
          </span>
          <Link href="/register" className="btn-primary text-xs px-4 py-2">Create free account</Link>
        </div>
      </nav>

      <main className="pt-24 pb-16 px-6 max-w-3xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight mb-4" style={{ color: "var(--color-text)" }}>
            Prueba sin registro
          </h1>
          <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
            Sube un CSV o Excel, lo limpiamos y te devolvemos el archivo listo.
          </p>
        </div>

        {!result ? (
          <div className="space-y-6">
            <div
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
              className="rounded-2xl border-2 border-dashed cursor-pointer transition-all p-16 flex flex-col items-center justify-center gap-4"
              style={{
                borderColor: dragOver ? "var(--color-accent)" : "var(--color-border)",
                backgroundColor: dragOver ? "var(--color-accent-dim)" : "var(--color-surface)",
              }}>
              <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ backgroundColor: "var(--color-accent-dim)" }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "var(--color-accent)" }}>
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <div className="text-center">
                <p className="text-sm font-medium" style={{ color: "var(--color-text)" }}>
                  {file ? file.name : "Arrastra tu archivo aqui o haz clic"}
                </p>
                <p className="text-xs mt-1" style={{ color: "var(--color-text-secondary)" }}>
                  CSV y Excel (.csv, .xlsx, .xls) — max 50MB
                </p>
              </div>
              <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls" className="hidden"
                onChange={e => { if (e.target.files?.[0]) handleFile(e.target.files[0]); }} />
            </div>

            {error && (
              <div className="p-4 rounded-lg text-sm" style={{ backgroundColor: "rgba(239,68,68,0.1)", color: "#EF4444" }}>
                {error}
              </div>
            )}

            {file && (
              <button onClick={handleClean} disabled={loading} className="btn-primary w-full py-4 text-base font-bold"
                style={{ opacity: loading ? 0.7 : 1 }}>
                {loading ? "Limpiando archivo..." : "Limpiar archivo"}
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl" style={{ backgroundColor: "var(--color-surface)", border: "1px solid rgba(16,185,129,0.3)" }}>
              <div className="flex items-center gap-3 mb-6">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: "#10B981" }} />
                <p className="text-sm font-semibold" style={{ color: "#10B981" }}>Archivo limpiado exitosamente</p>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {[
                  { label: "Filas antes",           value: result.rows_before },
                  { label: "Filas despues",          value: result.rows_after },
                  { label: "Duplicados eliminados",  value: result.duplicates_removed },
                  { label: "Nulos eliminados",       value: result.nulls_removed },
                  { label: "Columnas normalizadas",  value: result.columns_normalized },
                  { label: "Reduccion",              value: `${Math.round((1 - result.rows_after / Math.max(result.rows_before, 1)) * 100)}%` },
                ].map(stat => (
                  <div key={stat.label} className="p-4 rounded-lg" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                    <p className="text-xs mb-1" style={{ color: "var(--color-text-secondary)" }}>{stat.label}</p>
                    <p className="text-xl font-bold font-mono" style={{ color: "var(--color-accent)" }}>{stat.value}</p>
                  </div>
                ))}
              </div>
            </div>

            <button onClick={handleDownload} className="btn-primary w-full py-4 text-base font-bold">
              Descargar archivo limpio
            </button>

            <div className="flex gap-4">
              <button onClick={() => { setFile(null); setResult(null); }} className="btn-secondary flex-1 py-3 text-sm">
                Limpiar otro archivo
              </button>
              <Link href="/register" className="btn-primary flex-1 py-3 text-sm text-center">
                Crear cuenta — Acceso ilimitado
              </Link>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
