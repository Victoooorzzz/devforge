"use client";

import { useState, useEffect } from "react";
import { apiClient, trackEvent } from "@devforge/core";
import { 
  AlertTriangle, 
  CheckCircle2, 
  MessageSquare, 
  Copy, 
  Calendar, 
  TrendingUp, 
  Clock,
  Sparkles,
  Zap
} from "lucide-react";

interface FeedbackEntry {
  id: number;
  text: string;
  sentiment: "positive" | "negative" | "neutral" | null;
  confidence: number | null;
  themes: string[];
  is_urgent: boolean;
  draft_reply: string | null;
  created_at: string;
}

interface WeeklySummary {
  summary_text: string;
  generated_at: string;
  sentiment_stats: Record<string, number>;
}

const sentimentColors: Record<string, { backgroundColor: string; color: string; icon: any }> = {
  positive: { backgroundColor: "rgba(16,185,129,0.15)", color: "#10B981", icon: CheckCircle2 },
  negative: { backgroundColor: "rgba(239,68,68,0.15)", color: "#EF4444", icon: AlertTriangle },
  neutral: { backgroundColor: "rgba(163,163,163,0.15)", color: "#A3A3A3", icon: MessageSquare },
};

export default function DashboardPage() {
  const [entries, setEntries] = useState<FeedbackEntry[]>([]);
  const [summary, setSummary] = useState<WeeklySummary | null>(null);
  const [newText, setNewText] = useState("");
  const [analyzing, setAnalyzing] = useState<number | null>(null);
  const [copying, setCopying] = useState<number | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [entriesRes, summaryRes] = await Promise.all([
        apiClient.get<FeedbackEntry[]>("/feedback/list"),
        apiClient.get<WeeklySummary>("/feedback/summary/weekly")
      ]);
      setEntries(entriesRes.data);
      if (summaryRes.data) setSummary(summaryRes.data);
    } catch (err) {
      console.error("Error fetching data", err);
    }
  };

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

  const copyToClipboard = (text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopying(id);
    setTimeout(() => setCopying(null), 2000);
  };

  const counts = { 
    positive: entries.filter((e) => e.sentiment === "positive").length, 
    negative: entries.filter((e) => e.sentiment === "negative").length, 
    neutral: entries.filter((e) => e.sentiment === "neutral").length 
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight" style={{ color: "var(--color-text)" }}>
            Feedback Intelligence
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--color-text-secondary)" }}>
            Gemini-powered sentiment and urgency analysis
          </p>
        </div>
        <div className="flex gap-4">
          <div className="text-right">
            <p className="text-xs font-semibold uppercase opacity-50 mb-1">Total Entries</p>
            <p className="text-2xl font-bold">{entries.length}</p>
          </div>
          <div className="h-10 w-px bg-white/10 mx-2" />
          <div className="text-right text-red-500">
            <p className="text-xs font-semibold uppercase opacity-70 mb-1">Urgent Items</p>
            <p className="text-2xl font-bold">{entries.filter(e => e.is_urgent).length}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          {/* Stats Bar */}
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(counts).map(([key, val]) => {
              const config = sentimentColors[key];
              const Icon = config.icon;
              return (
                <div key={key} className="p-4 rounded-xl border border-white/5" style={{ backgroundColor: "var(--color-surface)" }}>
                  <div className="flex items-center gap-2 mb-2">
                    <Icon size={16} style={{ color: config.color }} />
                    <span className="text-xs font-bold uppercase tracking-wider opacity-60">{key}</span>
                  </div>
                  <p className="text-3xl font-mono font-bold" style={{ color: config.color }}>{val}</p>
                </div>
              );
            })}
          </div>

          {/* Add Feedback */}
          <section>
            <form onSubmit={handleAdd} className="relative group">
              <textarea 
                value={newText} 
                onChange={(e) => setNewText(e.target.value)} 
                className="w-full bg-black/20 border border-white/10 rounded-2xl p-6 pr-24 text-sm focus:border-indigo-500 outline-none transition-all resize-none min-h-[120px]" 
                placeholder="Paste raw user feedback here (app store reviews, emails, chat logs)..." 
                required 
              />
              <button 
                type="submit" 
                className="absolute bottom-4 right-4 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl font-bold text-sm flex items-center gap-2 transition-all shadow-lg"
              >
                <Zap size={16} />
                Analyze
              </button>
            </form>
          </section>

          {/* Feed */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-2 px-1">
              <Clock size={16} className="opacity-40" />
              <h2 className="text-xs font-bold uppercase tracking-widest opacity-40">Recent Activity</h2>
            </div>
            {entries.length === 0 && (
              <div className="p-12 text-center rounded-2xl border-2 border-dashed border-white/5 opacity-40">
                <p>No feedback entries found yet.</p>
              </div>
            )}
            {entries.map((entry) => {
              const config = entry.sentiment ? sentimentColors[entry.sentiment] : null;
              return (
                <div key={entry.id} className="group p-5 rounded-2xl border border-white/5 transition-all hover:border-white/20" style={{ backgroundColor: "var(--color-surface)" }}>
                  <div className="flex items-start justify-between gap-6 mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-3">
                        {entry.is_urgent && (
                          <span className="bg-red-500/20 text-red-500 text-[10px] font-black uppercase px-2 py-0.5 rounded-md animate-pulse border border-red-500/30">
                            Urgent
                          </span>
                        )}
                        <span className="text-[10px] font-mono opacity-30">
                          ID: {entry.id.toString().padStart(4, '0')} • {new Date(entry.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-[15px] leading-relaxed" style={{ color: "var(--color-text)" }}>{entry.text}</p>
                    </div>
                    
                    <div className="flex-shrink-0">
                      {entry.sentiment ? (
                        <div className="flex flex-col items-end">
                          <span className="text-[11px] font-black uppercase px-3 py-1 rounded-full mb-1" style={{ ...config }}>
                            {entry.sentiment}
                          </span>
                          <span className="text-[10px] opacity-40 font-mono">
                            {entry.confidence ? (entry.confidence * 100).toFixed(0) : "0"}% match
                          </span>
                        </div>
                      ) : (
                        <button 
                          onClick={() => handleAnalyze(entry.id)} 
                          disabled={analyzing === entry.id} 
                          className="bg-white/5 hover:bg-white/10 text-xs font-bold px-4 py-2 rounded-lg transition-all"
                        >
                          {analyzing === entry.id ? "Analyzing..." : "Process with AI"}
                        </button>
                      )}
                    </div>
                  </div>

                  {entry.themes.length > 0 && (
                    <div className="flex flex-wrap gap-2 pt-3 border-t border-white/5">
                      {entry.themes.map((t) => (
                        <span key={t} className="text-[10px] font-bold px-2.5 py-1 rounded-md bg-white/5 text-white/40 uppercase tracking-tight">
                          #{t}
                        </span>
                      ))}
                    </div>
                  )}

                  {entry.draft_reply && (
                    <div className="mt-4 p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/10 relative group/draft">
                      <div className="flex items-center gap-2 mb-2 text-indigo-400">
                        <Sparkles size={12} />
                        <span className="text-[10px] font-bold uppercase tracking-widest">AI Drafted Reply</span>
                      </div>
                      <p className="text-xs text-indigo-200/70 italic leading-relaxed pr-10">
                        "{entry.draft_reply}"
                      </p>
                      <button 
                        onClick={() => copyToClipboard(entry.draft_reply!, entry.id)}
                        className="absolute top-4 right-4 p-2 rounded-lg hover:bg-indigo-500/20 text-indigo-400 transition-all opacity-0 group-hover/draft:opacity-100"
                        title="Copy draft"
                      >
                        {copying === entry.id ? <CheckCircle2 size={16} /> : <Copy size={16} />}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <div className="p-6 rounded-2xl border border-indigo-500/20 bg-indigo-500/5 backdrop-blur-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400">
                <Calendar size={20} />
              </div>
              <h2 className="font-bold">Weekly Intelligence</h2>
            </div>
            
            {summary ? (
              <>
                <div className="space-y-4">
                  <p className="text-sm text-white/70 leading-relaxed italic">
                    "{summary.summary_text}"
                  </p>
                  
                  <div className="pt-4 border-t border-white/5">
                    <p className="text-[10px] font-bold uppercase tracking-widest opacity-40 mb-3">Volume Trend</p>
                    <div className="flex items-end gap-1 h-12">
                      {[34, 45, 23, 67, 89, 45, 56].map((h, i) => (
                        <div key={i} className="flex-1 bg-indigo-500/20 rounded-t-sm" style={{ height: `${h}%` }} />
                      ))}
                    </div>
                  </div>
                </div>
                <p className="text-[10px] mt-6 opacity-30 text-center">
                  Last generated on {new Date(summary.generated_at).toLocaleDateString()}
                </p>
              </>
            ) : (
              <div className="text-center py-10 opacity-30">
                <TrendingUp size={32} className="mx-auto mb-2 opacity-20" />
                <p className="text-xs">Summary will be ready next Monday morning.</p>
              </div>
            )}
          </div>

          <div className="p-6 rounded-2xl bg-white/5 border border-white/5">
            <h3 className="text-sm font-bold mb-4">Integration Tip</h3>
            <p className="text-xs text-white/50 leading-relaxed mb-4">
              Connect FeedbackLens to your Discord or Slack via webhooks to receive real-time alerts for "Urgent" entries.
            </p>
            <button className="w-full py-2.5 rounded-xl border border-white/10 text-xs font-bold hover:bg-white/5 transition-all">
              Setup Webhooks
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
