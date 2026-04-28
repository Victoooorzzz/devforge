"use client";
import { useState, useEffect, useRef } from "react";
import { apiClient, trackEvent } from "@devforge/core";

interface WebhookRequest {
  id: number;
  method: string;
  path: string;
  status_code: number;
  headers: Record<string, string>;
  body: string;
  received_at: string;
}

const methodColors: Record<string, string> = {
  GET: "#10B981", POST: "#6366F1", PUT: "#F59E0B", DELETE: "#EF4444", PATCH: "#8B5CF6",
};

export default function DashboardPage() {
  const [requests, setRequests] = useState<WebhookRequest[]>([]);
  const [selected, setSelected] = useState<WebhookRequest | null>(null);
  const [endpointUrl, setEndpointUrl] = useState("");
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    apiClient.get<{ endpoint_url: string }>("/webhooks/endpoint").then(({ data }) => setEndpointUrl(data.endpoint_url)).catch(() => {});
    
    const fetchRequests = async () => {
      try {
        const { data } = await apiClient.get<WebhookRequest[]>("/webhooks/requests");
        setRequests((prev) => {
          if (prev.length === 0) return data;
          const existingIds = new Set(prev.map(r => r.id));
          const newRequests = data.filter(r => !existingIds.has(r.id));
          return [...newRequests, ...prev].slice(0, 100);
        });
      } catch (e) {}
    };

    fetchRequests();
    intervalRef.current = setInterval(fetchRequests, 5000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const handleClearHistory = async () => {
    if (!window.confirm("¿Estás seguro de que deseas limpiar el historial de peticiones?")) return;
    trackEvent("feature_used", { feature_name: "clear_webhook_history" });
    try {
      await apiClient.delete("/webhooks/requests");
      setRequests([]);
      setSelected(null);
    } catch (err: any) {
      alert("Error al limpiar historial");
    }
  };

  const handleReplay = async (id: number) => {
    trackEvent("feature_used", { feature_name: "replay_webhook" });
    await apiClient.post(`/webhooks/requests/${id}/replay`);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: "var(--color-text)" }}>Incoming Requests</h1>
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium" style={{ backgroundColor: "rgba(16,185,129,0.1)", color: "#10B981" }}>
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
            En vivo
          </span>
        </div>
        <button 
          onClick={handleClearHistory} 
          className="text-xs font-medium px-3 py-1.5 rounded transition-colors"
          style={{ backgroundColor: "rgba(239,68,68,0.1)", color: "#EF4444" }}
        >
          Limpiar historial
        </button>
      </div>
      {endpointUrl && (
        <div className="flex items-center gap-3 mb-8 p-3 rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
          <span className="text-xs font-medium" style={{ color: "var(--color-text-secondary)" }}>Your endpoint:</span>
          <code className="text-sm font-mono px-2 py-1 rounded" style={{ backgroundColor: "var(--color-bg)", color: "var(--color-accent)" }}>{endpointUrl}</code>
          <button onClick={() => navigator.clipboard.writeText(endpointUrl)} className="text-xs" style={{ color: "var(--color-accent)" }}>Copy</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Request List */}
        <div className="lg:col-span-2 rounded-lg overflow-hidden" style={{ backgroundColor: "var(--color-surface)" }}>
          <table className="w-full">
            <thead><tr style={{ borderBottom: "1px solid var(--color-border)" }}>
              {["Method", "Path", "Time", ""].map((h) => (
                <th key={h} className="text-left text-xs font-medium uppercase tracking-wide px-4 py-3" style={{ color: "var(--color-text-secondary)" }}>{h}</th>
              ))}
            </tr></thead>
            <tbody>
              {requests.map((req) => (
                <tr key={req.id} className="cursor-pointer transition-colors duration-150" style={{ borderBottom: "1px solid rgba(38,38,38,0.15)", backgroundColor: selected?.id === req.id ? "var(--color-surface-raised)" : "transparent" }} onClick={() => setSelected(req)}>
                  <td className="px-4 py-3"><span className="text-xs font-mono font-semibold px-2 py-0.5 rounded" style={{ color: methodColors[req.method] || "#A3A3A3" }}>{req.method}</span></td>
                  <td className="px-4 py-3 text-sm font-mono truncate max-w-xs" style={{ color: "var(--color-text)" }}>{req.path}</td>
                  <td className="px-4 py-3 text-xs" style={{ color: "var(--color-text-secondary)" }}>{req.received_at}</td>
                  <td className="px-4 py-3 text-right"><button onClick={(e) => { e.stopPropagation(); handleReplay(req.id); }} className="text-xs font-medium" style={{ color: "var(--color-accent)" }}>Replay</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Detail Panel */}
        <div className="rounded-lg p-4" style={{ backgroundColor: "var(--color-surface)" }}>
          {selected ? (
            <div>
              <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-text)" }}>Request Detail</h3>
              <div className="mb-4"><p className="text-xs font-medium mb-1" style={{ color: "var(--color-text-secondary)" }}>Headers</p><pre className="text-xs font-mono p-3 rounded overflow-auto max-h-48" style={{ backgroundColor: "var(--color-bg)", color: "var(--color-text-secondary)" }}>{JSON.stringify(selected.headers, null, 2)}</pre></div>
              <div><p className="text-xs font-medium mb-1" style={{ color: "var(--color-text-secondary)" }}>Body</p><pre className="text-xs font-mono p-3 rounded overflow-auto max-h-64" style={{ backgroundColor: "var(--color-bg)", color: "var(--color-text)" }}>{selected.body}</pre></div>
            </div>
          ) : (
            <p className="text-sm text-center py-12" style={{ color: "var(--color-text-secondary)" }}>Select a request to inspect</p>
          )}
        </div>
      </div>
    </div>
  );
}
