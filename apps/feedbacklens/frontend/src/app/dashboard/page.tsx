"use client";
import { useState, useEffect } from "react";
import { apiClient, trackEvent } from "@devforge/core";

interface FeedbackEntry {
  id: number;
  text: string;
  sentiment: "positive" | "negative" | "neutral" | null;
  confidence: number | null;
  themes: string[];
  created_at: string;
}

const sentimentColors: Record<string, { bg: string; text: string }> = {
  positive: { bg: "rgba(16,185,129,0.15)", text: "#10B981" },
  negative: { bg: "rgba(239,68,68,0.15)", text: "#EF4444" },
  neutral: { bg: "rgba(163,163,163,0.15)", text: "#A3A3A3" },
};

export default function DashboardPage() {
  const [entries, setEntries] = useState<FeedbackEntry[]>([]);
  const [newText, setNewText] = useState("");
  const [analyzing, setAnalyzing] = useState<number | null>(null);

  useEffect(() => {
    apiClient.get<FeedbackEntry[]>("/feedback/list").then(({ data }) => setEntries(data)).catch(() => {});
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newText.trim()) return;
    trackEvent("feature_used", { feature_name: "add_feedback" });
    const { data } = await apiClient.post<FeedbackEntry>("/feedback", { text: newText });
    setEntries((prev) => [data, ...prev]);
    setNewText("");
  };

  const handleAnalyze = async (id: number) => {
    setAnalyzing(id);
    trackEvent("feature_used", { feature_name: "analyze_sentiment" });
    try {
      const { data } = await apiClient.post<FeedbackEntry>(`/feedback/${id}/analyze`);
      setEntries((prev) => prev.map((e) => (e.id === id ? data : e)));
    } finally {
      setAnalyzing(null);
    }
  };

  const counts = { positive: entries.filter((e) => e.sentiment === "positive").length, negative: entries.filter((e) => e.sentiment === "negative").length, neutral: entries.filter((e) => e.sentiment === "neutral").length };

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight mb-2" style={{ color: "var(--color-text)" }}>Feedback</h1>
      <p className="text-sm mb-8" style={{ color: "var(--color-text-secondary)" }}>{entries.length} entries analyzed</p>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {Object.entries(counts).map(([key, val]) => (
          <div key={key} className="p-4 rounded-lg text-center" style={{ backgroundColor: "var(--color-surface)" }}>
            <p className="text-2xl font-bold font-mono" style={{ color: sentimentColors[key]?.text }}>{val}</p>
            <p className="text-xs font-medium uppercase tracking-wide mt-1" style={{ color: "var(--color-text-secondary)" }}>{key}</p>
          </div>
        ))}
      </div>

      {/* Add Form */}
      <form onSubmit={handleAdd} className="flex gap-3 mb-8">
        <textarea value={newText} onChange={(e) => setNewText(e.target.value)} className="input-field flex-1 resize-none" rows={2} placeholder="Paste user feedback here..." required />
        <button type="submit" className="btn-primary self-end">Add</button>
      </form>

      {/* Entries */}
      <div className="space-y-3">
        {entries.map((entry) => (
          <div key={entry.id} className="p-4 rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
            <div className="flex items-start justify-between gap-4">
              <p className="text-sm flex-1" style={{ color: "var(--color-text)" }}>{entry.text}</p>
              <div className="flex items-center gap-3 flex-shrink-0">
                {entry.sentiment ? (
                  <span className="text-xs font-medium px-2.5 py-1 rounded-full" style={{ ...sentimentColors[entry.sentiment] }}>
                    {entry.sentiment} {entry.confidence ? `(${(entry.confidence * 100).toFixed(0)}%)` : ""}
                  </span>
                ) : (
                  <button onClick={() => handleAnalyze(entry.id)} disabled={analyzing === entry.id} className="text-xs font-medium px-3 py-1.5 rounded-md disabled:opacity-50" style={{ backgroundColor: "var(--color-accent-dim)", color: "var(--color-accent)" }}>
                    {analyzing === entry.id ? "Analyzing..." : "Analyze"}
                  </button>
                )}
              </div>
            </div>
            {entry.themes.length > 0 && (
              <div className="flex gap-2 mt-3">{entry.themes.map((t) => (<span key={t} className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-secondary)" }}>{t}</span>))}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
