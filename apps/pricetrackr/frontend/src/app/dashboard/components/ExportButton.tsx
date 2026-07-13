"use client";
import { useState, useRef, useEffect } from "react";
import { apiClient, downloadFile } from "@devforge/core";
import { Download, ChevronDown, Loader2, FileSpreadsheet, FileJson, AlertCircle, Check } from "lucide-react";

type ExportFormat = "csv" | "xlsx" | "json";

interface ExportJobResponse {
  id: string;
  status: string;
  format: string;
  r2_url: string | null;
  error_message: string | null;
}

interface ExportButtonProps {
  showToast: (toast: { tone: "success" | "error" | "info"; message: string }) => void;
}

export default function ExportButton({ showToast }: ExportButtonProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [currentJob, setCurrentJob] = useState<ExportJobResponse | null>(null);
  const [downloadReady, setDownloadReady] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Poll for job status
  useEffect(() => {
    if (!exporting || !currentJob) return;

    let active = true;
    let timer: NodeJS.Timeout;

    const checkJobStatus = async () => {
      try {
        const { data } = await apiClient.get<ExportJobResponse>(`/trackers/export/${currentJob.id}`);

        if (!active) return;

        setCurrentJob(data);

        if (data.status === "completed") {
          setExporting(false);
          setDownloadReady(true);
          showToast({ tone: "success", message: `Export complete! Download is ready.` });

          // Auto trigger download
          if (data.r2_url) {
            window.location.href = data.r2_url;
          }
        } else if (data.status === "failed") {
          setExporting(false);
          showToast({
            tone: "error",
            message: `Export failed: ${data.error_message || "Unknown error"}`,
          });
        } else {
          // Poll again in 1.5s
          timer = setTimeout(checkJobStatus, 1500);
        }
      } catch (err) {
        if (!active) return;
        setExporting(false);
        showToast({ tone: "error", message: "Error checking export progress." });
      }
    };

    timer = setTimeout(checkJobStatus, 1500);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [exporting, currentJob, showToast]);

  const handleTriggerExport = async (format: ExportFormat) => {
    setDropdownOpen(false);
    setExporting(true);
    setDownloadReady(false);
    setCurrentJob(null);
    showToast({ tone: "info", message: `Preparing your ${format.toUpperCase()} export...` });

    try {
      await downloadFile(`/trackers/export-file?format=${format}`, `pricetrackr-export.${format}`);
      setExporting(false);
      showToast({ tone: "success", message: `${format.toUpperCase()} export downloaded.` });
    } catch (err) {
      setExporting(false);
      showToast({ tone: "error", message: "Failed to initialize export job. Please retry." });
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {exporting ? (
        <button
          disabled
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium bg-zinc-900 border border-white/5 text-zinc-400 cursor-not-allowed"
        >
          <Loader2 className="w-4 h-4 animate-spin text-indigo-500" />
          <span>Exporting ({currentJob?.status || "pending"})...</span>
        </button>
      ) : downloadReady && currentJob?.r2_url ? (
        <div className="flex items-center gap-1">
          <a
            href={currentJob.r2_url}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20 transition-colors"
          >
            <Download className="w-4 h-4" />
            <span>Download {currentJob.format.toUpperCase()}</span>
          </a>
          <button
            onClick={() => setDownloadReady(false)}
            className="px-2 py-2 text-zinc-400 hover:text-white rounded-lg text-xs"
            title="Start new export"
          >
            Clear
          </button>
        </div>
      ) : (
        <>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium bg-zinc-900 hover:bg-zinc-800 border border-white/5 text-zinc-200 transition-colors"
          >
            <Download className="w-4 h-4" />
            <span>Export Data</span>
            <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${dropdownOpen ? "rotate-180" : ""}`} />
          </button>

          {dropdownOpen && (
            <div
              className="absolute right-0 top-full mt-2 w-48 rounded-xl shadow-xl z-50 overflow-hidden bg-zinc-950 border border-white/5 animate-in fade-in slide-in-from-top-2 duration-200"
            >
              <button
                onClick={() => handleTriggerExport("csv")}
                className="w-full flex items-center gap-2.5 text-left px-4 py-3 text-sm text-zinc-300 hover:bg-white/5 transition-colors"
              >
                <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
                <span>CSV Spreadsheet</span>
              </button>
              <button
                onClick={() => handleTriggerExport("xlsx")}
                className="w-full flex items-center gap-2.5 text-left px-4 py-3 text-sm text-zinc-300 hover:bg-white/5 transition-colors"
              >
                <FileSpreadsheet className="w-4 h-4 text-indigo-400" />
                <span>Excel Worksheets</span>
              </button>
              <button
                onClick={() => handleTriggerExport("json")}
                className="w-full flex items-center gap-2.5 text-left px-4 py-3 text-sm text-zinc-300 hover:bg-white/5 transition-colors"
              >
                <FileJson className="w-4 h-4 text-amber-400" />
                <span>JSON Feed</span>
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
