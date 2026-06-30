import { sql } from "../../lib/db";
import Link from "next/link";
import { Sparkles, ArrowRight, ShoppingCart, Activity } from "lucide-react";
import { Metadata } from "next";

export const revalidate = 3600; // Revalidate every hour

export const metadata: Metadata = {
  title: "Public Price Watchlist | PriceTrackr",
  description: "Browse product price trends tracked by our community. See historic lows and active discount opportunities.",
};

export default async function PublicProductsPage({
  searchParams,
}: {
  searchParams: { page?: string };
}) {
  const page = parseInt(searchParams.page || "1");
  const limit = 12;
  const offset = (page - 1) * limit;

  // Fetch count of public trackers
  const countRes = await sql`
    SELECT COUNT(*) FROM tracked_urls
    WHERE is_public = TRUE AND status != 'deleted'
  `;
  const total = parseInt(countRes[0].count);
  const totalPages = Math.ceil(total / limit);

  // Fetch paginated public trackers
  const products = await sql`
    SELECT id, label, url, current_price, min_price, in_stock, slug, last_checked
    FROM tracked_urls
    WHERE is_public = TRUE AND status != 'deleted'
    ORDER BY last_checked DESC NULLS LAST, created_at DESC
    LIMIT ${limit} OFFSET ${offset}
  `;

  return (
    <div className="min-h-screen bg-black text-white p-6 md:p-12">
      <div className="max-w-6xl mx-auto space-y-8">

        {/* Header */}
        <div className="text-center space-y-3 max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-bold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Community Watchlist</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white">
            Monitored Products & Deals
          </h1>
          <p className="text-sm text-zinc-400">
            Real-time price drop records from across the web. Explore recent pricing trends and historic lows monitored by our users.
          </p>
        </div>

        {/* Product Grid */}
        {products.length === 0 ? (
          <div className="text-center py-20 bg-zinc-950/40 border border-white/5 rounded-2xl">
            <p className="text-zinc-500 font-medium text-sm">No public tracked products available yet.</p>
            <Link
              href="/register"
              className="mt-4 inline-flex items-center gap-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold transition-colors"
            >
              <span>Watch your first product</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {products.map((p: any) => {
              const hasPrice = p.current_price !== null;
              const hasDrop = hasPrice && p.previous_price && p.current_price < p.previous_price;

              return (
                <div
                  key={p.id}
                  className="bg-zinc-950/30 border border-white/5 rounded-2xl p-5 flex flex-col justify-between hover:border-indigo-500/20 hover:bg-white/[0.01] transition-all duration-300 group"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-[9px] font-extrabold uppercase px-2 py-0.5 rounded ${
                          p.in_stock !== false
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/25"
                            : "bg-red-500/10 text-red-400 border border-red-500/25"
                        }`}
                      >
                        {p.in_stock !== false ? "In Stock" : "Out of Stock"}
                      </span>
                      {hasDrop && (
                        <span className="text-[9px] font-extrabold bg-indigo-500/10 text-indigo-400 border border-indigo-500/25 px-2 py-0.5 rounded uppercase tracking-wider">
                          Price Drop
                        </span>
                      )}
                    </div>

                    <div className="space-y-1">
                      <h3 className="text-base font-bold text-white group-hover:text-indigo-400 transition-colors line-clamp-2">
                        {p.label}
                      </h3>
                      <p className="text-[10px] text-zinc-500 truncate">{new URL(p.url).hostname}</p>
                    </div>
                  </div>

                  <div className="mt-6 pt-4 border-t border-white/5 flex items-center justify-between gap-4">
                    <div className="space-y-0.5">
                      <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider">Current Price</span>
                      <p className="text-base font-extrabold font-mono text-white">
                        {hasPrice ? `$${parseFloat(p.current_price).toFixed(2)}` : "—"}
                      </p>
                    </div>

                    <Link
                      href={`/p/${p.slug}`}
                      className="flex items-center gap-1 px-3.5 py-2 bg-zinc-900 border border-white/5 text-zinc-200 hover:text-white hover:bg-zinc-800 rounded-lg text-xs font-semibold transition-all"
                    >
                      <span>View History</span>
                      <Activity className="w-3.5 h-3.5 text-indigo-400" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 pt-6">
            <Link
              href={page > 1 ? `/p?page=${page - 1}` : "#"}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border ${
                page > 1
                  ? "bg-zinc-900 border-white/5 text-zinc-300 hover:bg-zinc-800"
                  : "bg-zinc-950/20 border-white/5 text-zinc-600 cursor-not-allowed"
              }`}
            >
              Previous
            </Link>

            <span className="text-xs text-zinc-500 font-medium">
              Page {page} of {totalPages}
            </span>

            <Link
              href={page < totalPages ? `/p?page=${page + 1}` : "#"}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border ${
                page < totalPages
                  ? "bg-zinc-900 border-white/5 text-zinc-300 hover:bg-zinc-800"
                  : "bg-zinc-950/20 border-white/5 text-zinc-600 cursor-not-allowed"
              }`}
            >
              Next
            </Link>
          </div>
        )}

      </div>
    </div>
  );
}
