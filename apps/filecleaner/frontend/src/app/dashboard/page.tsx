"use client";
import { useState, useCallback, useEffect } from "react";
import { uploadFile, trackEvent, apiClient } from "@devforge/core";

interface FileItem {
  id: string;
  name: string;
  size: number;
  status: "uploading" | "processing" | "complete" | "error";
  downloadUrl?: string;
}

export default function DashboardPage() {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const { data } = await apiClient.get<FileItem[]>("/files/list");
        const formattedData = data.map((f: any) => ({
          id: f.id.toString(),
          name: f.name,
          size: f.size,
          status: f.status,
          downloadUrl: f.download_url
        }));
        setFiles(formattedData);
      } catch (err) {}
    };
    fetchFiles();
  }, []);

  const handleDelete = async (fileId: string) => {
    if (!window.confirm("¿Estás seguro de que deseas eliminar este archivo?")) return;
    trackEvent("feature_used", { feature_name: "delete_file" });
    try {
      await apiClient.delete(`/files/${fileId}`);
      setFiles((prev) => prev.filter((f) => f.id !== fileId));
    } catch (err) {
      alert("Error al eliminar archivo");
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleFiles = useCallback(async (fileList: FileList) => {
    const newFiles: FileItem[] = Array.from(fileList).map((f) => ({
      id: crypto.randomUUID(),
      name: f.name,
      size: f.size,
      status: "uploading" as const,
    }));
    setFiles((prev) => [...newFiles, ...prev]);
    trackEvent("feature_used", { feature_name: "file_upload" });

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      const fileId = newFiles[i].id;
      try {
        const formData = new FormData();
        formData.append("file", file);
        setFiles((prev) => prev.map((f) => f.id === fileId ? { ...f, status: "processing" } : f));
        const { data } = await uploadFile("/files/upload", formData) as { data: { id: number, download_url: string }; status: number };
        setFiles((prev) => prev.map((f) => f.id === fileId ? { ...f, id: data.id.toString(), status: "complete", downloadUrl: data.download_url } : f));
      } catch {
        setFiles((prev) => prev.map((f) => f.id === fileId ? { ...f, status: "error" } : f));
      }
    }
  }, []);

  const statusColors: Record<string, { backgroundColor: string; color: string }> = {
    uploading: { backgroundColor: "rgba(245,158,11,0.15)", color: "#F59E0B" },
    processing: { backgroundColor: "rgba(99,102,241,0.15)", color: "#6366F1" },
    complete: { backgroundColor: "rgba(16,185,129,0.15)", color: "#10B981" },
    error: { backgroundColor: "rgba(239,68,68,0.15)", color: "#EF4444" },
  };

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight mb-2" style={{ color: "var(--color-text)" }}>Dashboard</h1>
      <p className="text-sm mb-8" style={{ color: "var(--color-text-secondary)" }}>Upload files to clean, compress, or convert.</p>

      {/* Dropzone */}
      <div
        className="relative rounded-lg p-12 text-center cursor-pointer transition-all duration-200 mb-8"
        style={{
          backgroundColor: dragging ? "var(--color-accent-dim)" : "var(--color-surface)",
          border: `2px dashed ${dragging ? "var(--color-accent)" : "var(--color-border)"}`,
        }}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => { const input = document.createElement("input"); input.type = "file"; input.multiple = true; input.onchange = (e) => { const f = (e.target as HTMLInputElement).files; if (f) handleFiles(f); }; input.click(); }}
      >
        <svg className="mx-auto mb-4" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: "var(--color-text-secondary)" }}><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        <p className="text-sm font-medium mb-1" style={{ color: "var(--color-text)" }}>Drop files here or click to upload</p>
        <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>PNG, JPEG, WebP, PDF — up to 50 MB each</p>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="rounded-lg overflow-hidden" style={{ backgroundColor: "var(--color-surface)" }}>
          <table className="w-full">
            <thead><tr style={{ borderBottom: "1px solid var(--color-border)" }}>
              {["Name", "Size", "Status", ""].map((h) => (
                <th key={h} className="text-left text-xs font-medium uppercase tracking-wide px-4 py-3" style={{ color: "var(--color-text-secondary)" }}>{h}</th>
              ))}
            </tr></thead>
            <tbody>
              {files.map((file) => (
                <tr key={file.id} style={{ borderBottom: "1px solid rgba(38,38,38,0.15)" }}>
                  <td className="px-4 py-3 text-sm font-medium" style={{ color: "var(--color-text)" }}>{file.name}</td>
                  <td className="px-4 py-3 text-sm font-mono" style={{ color: "var(--color-text-secondary)" }}>{formatSize(file.size)}</td>
                  <td className="px-4 py-3"><span className="text-xs font-medium px-2.5 py-1 rounded-full" style={{ backgroundColor: statusColors[file.status]?.backgroundColor || "rgba(255,255,255,0.1)", color: statusColors[file.status]?.color || "#fff" }}>{file.status}</span></td>
                  <td className="px-4 py-3 text-right">
                    {file.downloadUrl && <a href={file.downloadUrl} className="text-xs font-medium mr-3" style={{ color: "var(--color-accent)" }}>Download</a>}
                    {file.status !== "uploading" && file.status !== "processing" && (
                      <button onClick={() => handleDelete(file.id)} className="text-xs font-medium" style={{ color: "#EF4444" }}>Eliminar</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
