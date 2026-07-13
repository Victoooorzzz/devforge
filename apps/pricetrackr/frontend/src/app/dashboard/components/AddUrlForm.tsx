"use client";
import { useState } from "react";
import { Search, Loader2, ArrowRight, ArrowLeft, Plus, Globe, Check, AlertTriangle } from "lucide-react";
import { TrackedUrl } from "./DashboardClient";

interface DetectedMetadata {
  price: number | null;
  selector: string | null;
  in_stock: boolean;
  is_js_rendered: boolean;
  body_length: number;
  blocked?: boolean;
  fetch_engine?: "curl_cffi" | "httpx";
  status_code?: number;
}

interface AddUrlFormProps {
  onSuccess: (newTracker: TrackedUrl) => void;
  onCancel: () => void;
  showToast: (toast: { tone: "success" | "error" | "info"; message: string }) => void;
}

export default function AddUrlForm({ onSuccess, onCancel, showToast }: AddUrlFormProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // Step 1 values
  const [url, setUrl] = useState("");
  const [urlError, setUrlError] = useState("");

  // Step 2 values (populated from detection)
  const [label, setLabel] = useState("");
  const [detectedData, setDetectedData] = useState<DetectedMetadata | null>(null);
  const [selector1, setSelector1] = useState("");
  const [selector2, setSelector2] = useState("");
  const [selector3, setSelector3] = useState("");
  const [checkFrequencyHours, setCheckFrequencyHours] = useState(24);
  const [slackWebhookUrl, setSlackWebhookUrl] = useState("");
  const [discordWebhookUrl, setDiscordWebhookUrl] = useState("");

  const analyzeUrl = async (targetUrl: string): Promise<DetectedMetadata> => {
    const response = await fetch("/api/trackers/detect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: targetUrl }),
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({ detail: "Failed to parse product." }));
      throw { detail: errorBody.detail || "Failed to parse product.", status: response.status };
    }

    return response.json();
  };

  const createTracker = async (payload: Record<string, unknown>): Promise<TrackedUrl> => {
    const response = await fetch("/api/trackers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({ detail: "Failed to create tracker." }));
      throw { detail: errorBody.detail || "Failed to create tracker.", status: response.status };
    }

    return response.json();
  };

  const handleAnalyzeUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    const normalizedUrl = url.trim();
    if (!normalizedUrl) {
      const message = "URL is required.";
      setUrlError(message);
      showToast({ tone: "error", message });
      return;
    }
    if (!normalizedUrl.startsWith("http://") && !normalizedUrl.startsWith("https://")) {
      const message = "Please enter a valid HTTP or HTTPS URL.";
      setUrlError(message);
      showToast({ tone: "error", message });
      return;
    }

    try {
      new URL(normalizedUrl);
    } catch {
      const message = "Please enter a valid HTTP or HTTPS URL.";
      setUrlError(message);
      showToast({ tone: "error", message });
      return;
    }

    setUrlError("");
    setUrl(normalizedUrl);
    setLoading(true);
    try {
      const data = await analyzeUrl(normalizedUrl);
      setDetectedData(data);
      setSelector1(data.selector || "");

      // Attempt to generate a nice default label from URL domain + path
      try {
        const parsedUrl = new URL(normalizedUrl);
        const domain = parsedUrl.hostname.replace("www.", "");
        const pathParts = parsedUrl.pathname.split("/").filter(Boolean);
        const namePart = pathParts[pathParts.length - 1] || pathParts[0] || "Product";
        const cleanName = namePart
          .replace(/[-_]/g, " ")
          .replace(/\.[a-z0-9]+$/i, "") // Remove file extensions
          .split(" ")
          .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
          .join(" ")
          .substring(0, 30);

        setLabel(`${cleanName} (${domain})`);
      } catch {
        setLabel("New Tracked Product");
      }

      setStep(2);
      showToast({ tone: "success", message: "Product details analyzed successfully." });
    } catch (err: any) {
      showToast({
        tone: "error",
        message: err.detail || "Failed to parse product. Check the URL and try again.",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveTracker = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!label.trim()) {
      showToast({ tone: "error", message: "Please provide a label/name for the product." });
      return;
    }

    setSaving(true);
    try {
      const data = await createTracker({
        url,
        label,
        check_frequency_hours: checkFrequencyHours,
        selector_1: selector1 || null,
        selector_2: selector2 || null,
        selector_3: selector3 || null,
        slack_webhook_url: slackWebhookUrl || null,
        discord_webhook_url: discordWebhookUrl || null,
      });

      showToast({ tone: "success", message: `Successfully added ${label} to price monitoring.` });
      onSuccess(data);
    } catch (err: any) {
      showToast({
        tone: "error",
        message: err.detail || "Failed to create tracker. Plan limits might have been exceeded.",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-zinc-950/40 border border-white/5 rounded-xl p-6 mb-6">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/5">
        <h2 className="text-sm font-semibold text-white">
          {step === 1 ? "Step 1: Analyze Product Link" : "Step 2: Configure price monitor"}
        </h2>
        <span className="text-xs text-zinc-500 font-medium">Step {step} of 2</span>
      </div>

      {step === 1 ? (
        <form onSubmit={handleAnalyzeUrl} className="space-y-4">
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider">
              Product URL
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500">
                <Globe className="w-4 h-4" />
              </span>
              <input
                type="url"
                required
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  if (urlError) setUrlError("");
                }}
                placeholder="https://www.bestbuy.com/site/example-product/1234567.p"
                aria-invalid={urlError ? "true" : "false"}
                aria-describedby={urlError ? "product-url-error" : undefined}
                className="input-field w-full pl-10 text-sm"
              />
            </div>
            {urlError ? (
              <p id="product-url-error" className="text-[11px] font-semibold text-red-300">
                {urlError}
              </p>
            ) : null}
            <p className="text-[10px] text-zinc-500">
              Paste a product page with visible price HTML. Shopify-friendly URLs, Best Buy, Newegg, Gymshark, Allbirds, and Casper pages work best; Shopify JSON-LD helps detection stay stable.
            </p>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-zinc-900 border border-white/5 text-zinc-300 hover:bg-zinc-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-colors"
            >
              {loading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Search className="w-3.5 h-3.5" />
              )}
              <span>{loading ? "Analyzing..." : "Analyze URL"}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </form>
      ) : (
        <form onSubmit={handleSaveTracker} className="space-y-4">
          {detectedData?.is_js_rendered && (
            <div className="flex gap-2.5 bg-amber-500/5 border border-amber-500/10 p-3 rounded-lg text-amber-300">
              <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <div className="space-y-0.5 text-left">
                <p className="text-xs font-bold">JavaScript-Rendered (SPA) Page Detected</p>
                <p className="text-[10px] text-zinc-400">
                  This page has very low static HTML content and requires JavaScript execution. If automatic pricing fails, make sure to customize the CSS selectors below.
                </p>
              </div>
            </div>
          )}

          {detectedData?.blocked && (
            <div className="flex gap-2.5 bg-red-500/5 border border-red-500/10 p-3 rounded-lg text-red-300">
              <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <div className="space-y-0.5 text-left">
                <p className="text-xs font-bold">Anti-bot challenge detected</p>
                <p className="text-[10px] text-zinc-400">
                  This store returned a CAPTCHA, Cloudflare, or access-denied page. You can still save the monitor, but reliable tracking may require a different product page or a managed scraping provider.
                </p>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                Product Name
              </label>
              <input
                type="text"
                required
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="iPhone 15 Pro Max"
                className="input-field w-full text-sm"
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                Check Interval
              </label>
              <select
                value={checkFrequencyHours}
                onChange={(e) => setCheckFrequencyHours(parseFloat(e.target.value))}
                className="input-field w-full text-sm cursor-pointer"
              >
                <option value="0.1666666667">Every 10 Minutes (Team)</option>
                <option value={1}>Every Hour</option>
                <option value={6}>Every 6 Hours</option>
                <option value={12}>Every 12 Hours</option>
                <option value={24}>Every 24 Hours</option>
              </select>
            </div>
          </div>

          <div className="bg-zinc-950/20 border border-white/5 rounded-lg p-3 space-y-2">
            <h3 className="text-xs font-bold text-zinc-300 uppercase tracking-wider">
              Automatic Scrape Results
            </h3>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-2 rounded bg-zinc-900 border border-white/5">
                <span className="text-zinc-500 block mb-0.5">Detected Price</span>
                <span className="font-bold text-indigo-400 font-mono">
                  {detectedData?.price ? `$${detectedData.price.toFixed(2)}` : "Not detected"}
                </span>
              </div>
              <div className="p-2 rounded bg-zinc-900 border border-white/5">
                <span className="text-zinc-500 block mb-0.5">Stock Status</span>
                <span
                  className={`font-semibold ${
                    detectedData?.in_stock ? "text-emerald-400" : "text-red-400"
                  }`}
                >
                  {detectedData?.in_stock ? "In Stock" : "Out of Stock"}
                </span>
              </div>
            </div>
            <p className="text-[10px] text-zinc-500">
              Fetch engine: {detectedData?.fetch_engine === "curl_cffi" ? "Chrome impersonation" : "standard HTTP"}{detectedData?.status_code ? ` · HTTP ${detectedData.status_code}` : ""}
            </p>
          </div>

          <details className="group border border-white/5 rounded-lg">
            <summary className="flex items-center justify-between cursor-pointer p-3 select-none text-xs font-bold text-zinc-400 hover:text-white uppercase tracking-wider">
              <span>Advanced Selectors & Webhooks</span>
              <ChevronDown className="w-4 h-4 transition-transform group-open:rotate-180" />
            </summary>

            <div className="p-3 border-t border-white/5 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <label className="block text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                    Primary CSS Selector
                  </label>
                  <input
                    type="text"
                    value={selector1}
                    onChange={(e) => setSelector1(e.target.value)}
                    placeholder="#price, .price"
                    className="input-field w-full text-xs font-mono"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="block text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                    Fallback Selector 2
                  </label>
                  <input
                    type="text"
                    value={selector2}
                    onChange={(e) => setSelector2(e.target.value)}
                    placeholder=".product-price"
                    className="input-field w-full text-xs font-mono"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="block text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                    Fallback Selector 3
                  </label>
                  <input
                    type="text"
                    value={selector3}
                    onChange={(e) => setSelector3(e.target.value)}
                    placeholder="span[itemprop='price']"
                    className="input-field w-full text-xs font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="block text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                    Slack Alert Webhook URL
                  </label>
                  <input
                    type="url"
                    value={slackWebhookUrl}
                    onChange={(e) => setSlackWebhookUrl(e.target.value)}
                    placeholder="https://hooks.slack.com/services/..."
                    className="input-field w-full text-xs"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="block text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                    Discord Alert Webhook URL
                  </label>
                  <input
                    type="url"
                    value={discordWebhookUrl}
                    onChange={(e) => setDiscordWebhookUrl(e.target.value)}
                    placeholder="https://discord.com/api/webhooks/..."
                    className="input-field w-full text-xs"
                  />
                </div>
              </div>
            </div>
          </details>

          <div className="flex items-center justify-between gap-2 pt-2">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-zinc-900 border border-white/5 text-zinc-300 hover:bg-zinc-800 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back</span>
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-zinc-900 border border-white/5 text-zinc-300 hover:bg-zinc-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-colors"
              >
                {saving ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Plus className="w-3.5 h-3.5" />
                )}
                <span>{saving ? "Creating monitor..." : "Start price monitor"}</span>
              </button>
            </div>
          </div>
        </form>
      )}
    </div>
  );
}

// Simple helper Chevron Icon inside the summary
function ChevronDown(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={props.className}
      {...props}
    >
      <polyline points="6 9 12 15 18 9"></polyline>
    </svg>
  );
}
