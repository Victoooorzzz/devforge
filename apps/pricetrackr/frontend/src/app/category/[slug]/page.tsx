import Link from "next/link";
import { ChevronLeft, PackageOpen } from "lucide-react";
import { Metadata } from "next";

export const revalidate = 3600;

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const categoryName = params.slug
    .replace(/-/g, " ")
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");

  return {
    title: `${categoryName} Price Trends | PriceTrackr`,
    description: `Track real-time pricing updates and historic drops in the ${categoryName} category.`,
  };
}

export default async function CategoryPage({ params }: { params: { slug: string } }) {
  const categoryName = params.slug
    .replace(/-/g, " ")
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");

  return (
    <div className="min-h-screen bg-black text-white p-6 md:p-12 flex items-center justify-center">
      <div className="max-w-md w-full space-y-6 text-center">

        <Link
          href="/p"
          className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-white transition-colors uppercase tracking-wider font-bold"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          <span>Back to watchlist</span>
        </Link>

        <div className="bg-zinc-950/30 border border-white/5 rounded-2xl p-8 space-y-4">
          <PackageOpen className="w-12 h-12 text-indigo-500 mx-auto" />
          <h1 className="text-xl font-extrabold text-white">{categoryName}</h1>
          <p className="text-xs text-zinc-400 leading-relaxed">
            We are currently indexing and organizing tracked product links for the {categoryName} category. Check back soon for curated price analytics.
          </p>
        </div>

      </div>
    </div>
  );
}
