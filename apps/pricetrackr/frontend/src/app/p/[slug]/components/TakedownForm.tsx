"use client";
import { useState } from "react";
import { Loader2, ShieldCheck, AlertCircle } from "lucide-react";

interface TakedownFormProps {
  slug: string;
  apiUrl: string;
}

export default function TakedownForm({ slug, apiUrl }: TakedownFormProps) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      const res = await fetch(`${apiUrl}/public/pricetrackr/slug/${slug}/takedown`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, reason }),
      });

      if (!res.ok) {
        throw new Error("Failed to submit takedown request");
      }

      setSuccess(true);
      setTimeout(() => {
        // Reload page to reflect that it is unpublished (it will return 404 since is_public = false)
        window.location.reload();
      }, 3000);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="bg-emerald-500/10 border border-emerald-500/20 p-4 rounded-xl text-emerald-400 text-center space-y-2">
        <ShieldCheck className="w-6 h-6 mx-auto" />
        <p className="text-sm font-semibold">Takedown Request Approved</p>
        <p className="text-xs text-zinc-400">
          This product has been unpublished from our search engine immediately. Reloading page...
        </p>
      </div>
    );
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="text-[10px] text-zinc-500 hover:text-red-400 font-semibold transition-colors uppercase tracking-wider block mx-auto py-2"
      >
        ⚠️ Request Content Takedown
      </button>
    );
  }

  return (
    <div className="bg-zinc-950/40 border border-white/5 p-4 rounded-xl max-w-md mx-auto space-y-4">
      <div className="flex items-center justify-between border-b border-white/5 pb-2">
        <span className="text-xs font-bold text-white uppercase tracking-wider">
          Content Takedown Request
        </span>
        <button
          onClick={() => setOpen(false)}
          className="text-[10px] text-zinc-500 hover:text-white uppercase font-bold"
        >
          Cancel
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3 text-left">
        <div className="space-y-1">
          <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
            Your Email
          </label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="owner@brand.com"
            className="input-field w-full text-xs"
          />
        </div>

        <div className="space-y-1">
          <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
            Reason for Takedown
          </label>
          <textarea
            required
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Please specify if this is a trademark infringement or proprietary brand link."
            className="input-field w-full text-xs resize-none"
          />
        </div>

        {error && (
          <div className="flex items-center gap-1.5 text-red-400 text-[10px]">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>{error}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full flex items-center justify-center gap-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold transition-colors"
        >
          {submitting ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <span>Unpublish Product Immediately</span>
          )}
        </button>
      </form>
    </div>
  );
}
