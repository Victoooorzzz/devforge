"use client";
import { useState, useCallback, useEffect, useRef } from "react";
import { trackEvent, apiClient } from "@devforge/core";
import { FileText, Download, Trash2, CheckCircle, Clock, AlertCircle, Info, ChevronDown, ChevronUp, Sparkles, RefreshCw, TrendingDown, Zap } from "lucide-react";

interface FileReport {
  rows_original: number;
  rows_clean: number;
  duplicates_removed: number;
  empty_removed: number;
  whitespace_fixed: number;
  rows_saved: number;
  reduction_pct: number;
}

interface FileItem {
  id: string;
  name: string;
  size: number;
  status: "queued" | "processing" | "complete" | "error";
  downloadUrl?: string;
  report?: FileReport;
  error?: string;
  localOnly?: boolean; // true while uploading before we have a server ID
}

const POLL_INTERVAL_MS = 2500;

export default function DashboardPage() {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [dragging, setDragging] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const pollingIds = useRef<Set<string>>(new Set());

  // Load existing files from API on mount
  useEffect(() => {
    apiClient.get<any[]>("/files/list").then(({ data }) => {
      setFiles(data.map((f: any) => ({
        id: f.id.toString(),
        name: f.name,
        size: f.size,
        status: f.status,
        downloadUrl: f.download_url,
        report: f.report ?? undefined,
      })));
    }).catch(() => {});
  }, []);

  // Auto-poll files that are in queued/processing state
  useEffect(() => {
    const interval = setInterval(async () => {
      const pendingFiles = files.filter(f =>
        (f.status === "queued" || f.status === "processing") && !f.localOnly
      );
      for (const f of pendingFiles) {
        if (pollingIds.current.has(f.id)) continue; // prevent overlap
        pollingIds.current.add(f.id);
        try {
          const { data } = await apiClient.get<any>(`/files/${f.id}/status`);
          setFiles(prev => prev.map(pf => pf.id === f.id ? {
            ...pf,
            status: data.status,
            downloadUrl: data.download_url,
            report: data.report,
            error: data.error,
          } : pf));
        } catch {
          // ignore transient errors
        } finally {
          pollingIds.current.delete(f.id);
        }
      }
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [files]);

  const handleDelete = async (fileId: string) => {
    if (!window.confirm("¿Eliminar este archivo?")) return;
    trackEvent("feature_used", { feature_name: "delete_file" });
    try {
      await apiClient.delete(`/files/${fileId}`);
      setFiles(prev => prev.filter(f => f.id !== fileId));
    } catch {
      alert("Error al eliminar archivo");
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleFiles = useCallback(async (fileList: FileList) => {
    const newFiles: FileItem[] = Array.from(fileList).map(f => ({
      id: crypto.randomUUID(),
      name: f.name,
      size: f.size,
      status: "queued" as const,
      localOnly: true,
    }));
    setFiles(prev => [...newFiles, ...prev]);
    trackEvent("feature_used", { feature_name: "file_upload" });

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      const tempId = newFiles[i].id;
      try {
        const formData = new FormData();
        formData.append("file", file);

        // Use fetch directly for multipart (apiClient wraps it)
        const token = typeof window !== "undefined" ? localStorage.getItem("devforge_token") : null;
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}/files/upload`, {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || "Upload failed");
        }
        const data = await res.json();

        setFiles(prev => prev.map(f => f.id === tempId ? {
          ...f,
          id: data.id.toString(),
          status: data.status,
          localOnly: false,
        } : f));
      } catch (e: any) {
        setFiles(prev => prev.map(f => f.id === tempId ? { ...f, status: "error", error: e.message } : f));
      }
    }
  }, []);

  const statusIcon = (status: string) => {
    if (status === "queued") return <Clock className="text-amber-500" size={16} />;
    if (status === "processing") return <RefreshCw className="animate-spin text-indigo-500" size={16} />;
    if (status === "complete") return <CheckCircle className="text-emerald-500" size={16} />;
    return <AlertCircle className="text-red-500" size={16} />;
  };

  const statusLabel: Record<string, string> = {
    queued: "En cola",
    processing: "Procesando...",
    complete: "Completo",
    error: "Error",
  };

  return (
    <div className="max-w-5xl mx-auto py-10 px-4">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2" style={{ color: "var(--color-text)" }}>
            Data Cleaning Hub
          </h1>
          <p className="text-sm opacity-60" style={{ color: "var(--color-text)" }}>
            Smart normalization for CSV and Excel datasets. Up to 200MB.
          </p>
        </div>
      </div>

      {/* Drop Zone */}
      <div
        className="relative rounded-2xl p-16 text-center cursor-pointer transition-all duration-300 mb-10 group"
        style={{
          backgroundColor: dragging ? "rgba(var(--color-primary-rgb), 0.05)" : "var(--color-surface)",
          border: `2px dashed ${dragging ? "var(--color-primary)" : "var(--color-border)"}`,
        }}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => {
          const input = document.createElement("input");
          input.type = "file";
          input.accept = ".csv,.xlsx,.xls";
          input.multiple = true;
          input.onchange = e => { const f = (e.target as HTMLInputElement).files; if (f) handleFiles(f); };
          input.click();
        }}
      >
        <div className="mx-auto w-16 h-16 rounded-full bg-black/5 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
          <FileText size={32} className="text-[var(--color-primary)]" />
        </div>
        <p className="text-lg font-semibold mb-2" style={{ color: "var(--color-text)" }}>
          Drop files here or click to upload
        </p>
        <p className="text-xs opacity-50" style={{ color: "var(--color-text)" }}>
          CSV, XLSX, XLS — up to 200MB — processed asynchronously
        </p>
      </div>

      {/* File List */}
      <div className="space-y-4">
        {files.map(file => {
          const isExpanded = expandedId === file.id;
          const isPending = file.status === "queued" || file.status === "processing";
          return (
            <div key={file.id} className="rounded-xl overflow-hidden transition-all duration-200" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
              <div
                className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer hover:bg-black/5"
                onClick={() => file.report && setExpandedId(isExpanded ? null : file.id)}
              >
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div className="p-2 rounded-lg bg-black/5">
                    {statusIcon(file.status)}
                  </div>
                  <div className="truncate">
                    <h3 className="text-sm font-medium truncate" style={{ color: "var(--color-text)" }}>{file.name}</h3>
                    <p className="text-xs opacity-50" style={{ color: "var(--color-text)" }}>{formatSize(file.size)}</p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {/* Status Badge */}
                  <div className="flex items-center gap-2">
                    {isPending && (
                      <div className="flex items-center gap-1.5">
                        <div className="w-24 h-1.5 rounded-full bg-black/10 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-[var(--color-primary)] transition-all"
                            style={{
                              width: file.status === "queued" ? "15%" : "65%",
                              animation: "pulse 1.5s ease-in-out infinite"
                            }}
                          />
                        </div>
                        <span className="text-[10px] font-bold text-[var(--color-primary)]">{statusLabel[file.status]}</span>
                      </div>
                    )}
                    {!isPending && (
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded ${
                        file.status === "complete" ? "bg-emerald-500/10 text-emerald-500" :
                        file.status === "error" ? "bg-red-500/10 text-red-500" : "bg-black/5"
                      }`}>
                        {statusLabel[file.status]}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {file.downloadUrl && (
                      <a
                        href={`${process.env.NEXT_PUBLIC_API_URL || ""}${file.downloadUrl}`}
                        className="p-2 rounded-lg hover:bg-[var(--color-primary)]/10 text-[var(--color-primary)] transition-colors"
                        title="Download Cleaned File"
                        onClick={e => e.stopPropagation()}
                      >
                        <Download size={18} />
                      </a>
                    )}
                    <button
                      onClick={e => { e.stopPropagation(); handleDelete(file.id); }}
                      className="p-2 rounded-lg hover:bg-red-500/10 text-red-500/60 hover:text-red-500 transition-colors"
                    >
                      <Trash2 size={18} />
                    </button>
                    {file.report && (isExpanded ? <ChevronUp size={20} className="opacity-30" /> : <ChevronDown size={20} className="opacity-30" />)}
                  </div>
                </div>
              </div>

              {/* Report Panel */}
              {isExpanded && file.report && (
                <div className="p-6 border-t border-[var(--color-border)] bg-black/5 animate-in fade-in slide-in-from-top-2 duration-300">
                  {/* Summary Banner */}
                  <div className="flex items-center gap-3 mb-6 p-4 rounded-xl" style={{ backgroundColor: "rgba(var(--color-primary-rgb), 0.08)", border: "1px solid rgba(var(--color-primary-rgb), 0.15)" }}>
                    <Zap size={20} className="text-[var(--color-primary)]" />
                    <div>
                      <p className="text-sm font-bold text-[var(--color-primary)]">
                        {file.report.reduction_pct > 0
                          ? `${file.report.reduction_pct}% size reduction — ${file.report.rows_saved.toLocaleString()} rows cleaned`
                          : "File is already clean!"}
                      </p>
                      <p className="text-xs opacity-60">Processed successfully</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 mb-4 text-[var(--color-primary)]">
                    <Info size={16} />
                    <h4 className="text-xs font-bold uppercase tracking-wider">Cleaning Intelligence Report</h4>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    {[
                      { label: "Total Rows", value: file.report.rows_original.toLocaleString(), color: "text-[var(--color-text)]" },
                      { label: "Clean Rows", value: file.report.rows_clean.toLocaleString(), color: "text-emerald-500" },
                      { label: "Duplicates", value: file.report.duplicates_removed.toLocaleString(), color: "text-indigo-400" },
                      { label: "Empty Rows", value: file.report.empty_removed.toLocaleString(), color: "text-amber-500" },
                      { label: "Text Fixes", value: file.report.whitespace_fixed.toLocaleString(), color: "text-sky-400" },
                    ].map(stat => (
                      <div key={stat.label} className="p-3 rounded-lg bg-white/5 border border-white/5">
                        <p className="text-[10px] uppercase font-bold opacity-40 mb-1">{stat.label}</p>
                        <p className={`text-lg font-mono font-bold ${stat.color}`}>{stat.value}</p>
                      </div>
                    ))}
                  </div>

                  {file.report.reduction_pct > 0 && (
                    <div className="mt-4 flex items-center gap-2 text-xs text-emerald-500">
                      <TrendingDown size={14} />
                      <span>{file.report.reduction_pct}% fewer rows after cleaning</span>
                    </div>
                  )}
                </div>
              )}

              {/* Error Message */}
              {file.status === "error" && file.error && (
                <div className="px-6 py-4 border-t border-red-500/20 bg-red-500/5">
                  <p className="text-xs text-red-500">{file.error}</p>
                </div>
              )}
            </div>
          );
        })}

        {files.length === 0 && (
          <div className="text-center py-20 opacity-20 border-2 border-dashed border-[var(--color-border)] rounded-2xl">
            <Sparkles size={48} className="mx-auto mb-4" />
            <p className="text-sm font-medium">Ready to clean your first dataset.</p>
          </div>
        )}
      </div>
    </div>
  );
}
