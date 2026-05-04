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
  const [requests, setRequests]     = useState<WebhookRequest[]>([]);
  const [selected, setSelected]     = useState<WebhookRequest | null>(null);
  const [endpointUrl, setEndpointUrl] = useState("");
  const [search, setSearch]         = useState("");
  const [copied, setCopied]         = useState(false);
  const intervalRef                 = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    apiClient.get<{ endpoint_url: string }>("/webhooks/endpoint")
      .then(({ data }) => setEndpointUrl(data.endpoint_url)).catch(() => {});

    const fetchRequests = async () => {
      try {
        const { data } = await apiClient.get<WebhookRequest[]>("/webhooks/requests");
        setRequests(prev => {
          if (prev.length === 0) return data;
          const existingIds = new Set(prev.map(r => r.id));
          const newReqs = data.filter(r => !existingIds.has(r.id));
          return [...newReqs, ...prev].slice(0, 100);
        });
      } catch {}
    };

    fetchRequests();
    intervalRef.current = setInterval(fetchRequests, 5000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, []);

  const handleClearHistory = async () => {
    if (!window.confirm("Seguro que quieres limpiar el historial?")) return;
    trackEvent("feature_used", { feature_name: "clear_webhook_history" });
    try {
      await apiClient.delete("/webhooks/requests");
      setRequests([]);
      setSelected(null);
    } catch { alert("Error al limpiar historial"); }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(endpointUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRetry = async (req: WebhookRequest) => {
    trackEvent("feature_used", { feature_name: "retry_webhook" });
    try {
      await apiClient.post(`/webhooks/requests/${req.id}/retry`);
      alert("Webhook reenviado");
    } catch { alert("Error al reenviar webhook"); }
  };

  const filtered = requests.filter(r => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      r.body.toLowerCase().includes(q) ||
      r.path.toLowerCase().includes(q) ||
      r.method.toLowerCase().includes(q)
    );
  });

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  return (
    <div className="flex gap-6 h-full">
      <div className="flex-1 min-w-0">

        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "var(--color-text)" }}>Webhook Monitor</h1>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: "#10B981" }} />
              <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>En vivo &middot; actualizando cada 5s</p>
            </div>
          </div>
          <button onClick={handleClearHistory} className="btn-secondary text-xs">Limpiar historial</button>
        </div>

        {endpointUrl && (
          <div className="p-4 rounded-lg mb-6 flex items-center justify-between gap-4" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="min-w-0">
              <p className="text-xs font-medium mb-1" style={{ color: "var(--color-text-secondary)" }}>Tu endpoint</p>
              <p className="text-sm font-mono truncate" style={{ color: "var(--color-accent)" }}>{endpointUrl}</p>
            </div>
            <button onClick={handleCopy} className="btn-secondary text-xs flex-shrink-0">
              {copied ? "Copiado!" : "Copiar"}
            </button>
          </div>
        )}

        <div className="mb-4">
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="input-field"
            placeholder="Buscar en body, path o metodo..."
          />
        </div>

        <div className="rounded-lg overflow-hidden" style={{ backgroundColor: "var(--color-surface)" }}>
          {filtered.length === 0 ? (
            <div className="p-12 text-center">
              <p className="text-sm font-mono" style={{ color: "var(--color-text-secondary)" }}>
                {search ? "Sin resultados para tu busqueda" : "Esperando webhooks..."}
              </p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                  {["Hora", "Metodo", "Path", ""].map((h, i) => (
                    <th key={i} className="text-left text-xs font-medium uppercase tracking-wide px-4 py-3"
                      style={{ color: "var(--color-text-secondary)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map(req => (
                  <tr key={req.id}
                    onClick={() => setSelected(req)}
                    className="cursor-pointer transition-colors"
                    style={{
                      borderBottom: "1px solid rgba(38,38,38,0.15)",
                      backgroundColor: selected?.id === req.id ? "var(--color-surface-raised)" : "transparent",
                    }}>
                    <td className="px-4 py-3 text-xs font-mono" style={{ color: "var(--color-text-secondary)" }}>{formatTime(req.received_at)}</td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-bold font-mono px-2 py-0.5 rounded"
                        style={{ backgroundColor: `${methodColors[req.method] || "#A3A3A3"}20`, color: methodColors[req.method] || "#A3A3A3" }}>
                        {req.method}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs font-mono truncate max-w-xs" style={{ color: "var(--color-text)" }}>{req.path}</td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={e => { e.stopPropagation(); handleRetry(req); }}
                        className="text-xs px-2 py-1 rounded transition-colors"
                        style={{ backgroundColor: "var(--color-surface-high)", color: "var(--color-text-secondary)" }}>
                        Reenviar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {selected && (
        <div className="w-96 flex-shrink-0 rounded-lg p-4 overflow-auto" style={{ backgroundColor: "var(--color-surface)", maxHeight: "calc(100vh - 8rem)" }}>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Inspector</p>
            <button onClick={() => setSelected(null)} className="text-xs" style={{ color: "var(--color-text-secondary)" }}>Cerrar</button>
          </div>
          <div className="space-y-4">
            <div>
              <p className="text-xs font-medium mb-2 uppercase tracking-wide" style={{ color: "var(--color-text-secondary)" }}>Headers</p>
              <pre className="text-xs p-3 rounded overflow-auto" style={{ backgroundColor: "var(--color-bg)", color: "var(--color-text)", maxHeight: "150px" }}>
                {JSON.stringify(selected.headers, null, 2)}
              </pre>
            </div>
            <div>
              <p className="text-xs font-medium mb-2 uppercase tracking-wide" style={{ color: "var(--color-text-secondary)" }}>Body</p>
              <pre className="text-xs p-3 rounded overflow-auto" style={{ backgroundColor: "var(--color-bg)", color: "var(--color-text)", maxHeight: "300px" }}>
                {(() => { try { return JSON.stringify(JSON.parse(selected.body), null, 2); } catch { return selected.body; } })()}
              </pre>
            </div>
            <button onClick={() => handleRetry(selected)} className="btn-primary w-full text-xs">
              Reenviar este webhook
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
