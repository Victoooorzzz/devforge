// packages/ui/components/ProductCard.tsx
import React from "react";

export interface ProductInfo {
  slug: string;
  name: string;
  tagline: string;
  domain: string;
  accentColor: string;
  price: number;
  status: "live" | "beta" | "coming-soon";
  problem?: string;
  solution?: string;
  audienceTags?: string[];
}

interface ProductCardProps {
  product: ProductInfo;
}

const statusLabels: Record<ProductInfo["status"], string> = {
  live: "Live",
  beta: "Beta pilot",
  "coming-soon": "Coming Soon",
};

export function ProductCard({ product }: ProductCardProps) {
  return (
    <a
      id={`product-${product.slug}`}
      href={`https://${product.domain}`}
      target="_blank"
      rel="noopener noreferrer"
      className="product-suite-card group flex flex-col rounded-lg p-6 transition-all duration-300 hover:translate-y-[-2px] animate-slide-up"
      style={{
        backgroundColor: "var(--color-surface)",
        "--card-accent": product.accentColor,
      } as React.CSSProperties}
    >
      <div className="flex items-start justify-between mb-4">
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold"
          style={{
            backgroundColor: `${product.accentColor}20`,
            color: product.accentColor,
          }}
        >
          {product.name.charAt(0)}
        </div>
        <span
          className="text-xs font-medium px-2.5 py-1 rounded-full"
          style={{
            backgroundColor:
              product.status === "live"
                ? "rgba(16,185,129,0.15)"
                : product.status === "beta"
                  ? "rgba(163,163,163,0.12)"
                  : "rgba(163,163,163,0.15)",
            color:
              product.status === "live"
                ? "#10B981"
                : product.status === "beta"
                  ? "var(--color-text-secondary)"
                  : "var(--color-text-secondary)",
          }}
        >
          {statusLabels[product.status]}
        </span>
      </div>

      <h3
        className="mb-2 text-lg font-semibold leading-tight"
        style={{ color: "var(--color-text)" }}
      >
        {product.name}
      </h3>
      <p
        className="mb-5 min-h-[3.5rem] text-sm leading-relaxed"
        style={{ color: "var(--color-text-secondary)" }}
      >
        {product.tagline}
      </p>

      {(product.problem || product.solution || product.audienceTags?.length) && (
        <div className="mb-5 space-y-3 border-t pt-4 text-sm leading-relaxed" style={{ borderColor: "var(--color-border)", color: "var(--color-text-secondary)" }}>
          {product.problem && <p className="break-words"><strong style={{ color: "var(--color-text)" }}>Problem:</strong> {product.problem}</p>}
          {product.solution && <p className="break-words"><strong style={{ color: "var(--color-text)" }}>Solution:</strong> {product.solution}</p>}
          {product.audienceTags?.length ? (
            <div className="flex flex-wrap gap-2 pt-1">
              {product.audienceTags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-white/10 px-2.5 py-1 text-xs"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {tag}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      )}

      <div className="mt-auto flex items-center justify-between gap-3">
        <span
          className="text-sm font-mono font-semibold"
          style={{ color: product.accentColor }}
        >
          ${product.price}/mo
        </span>
        <span
          className="inline-flex shrink-0 items-center rounded-md border px-3 py-2 text-xs font-semibold transition group-hover:border-[color:var(--card-accent)]"
          style={{ color: "var(--color-text)", borderColor: "rgba(255,255,255,0.14)" }}
        >
          Try Live Demo
        </span>
      </div>
    </a>
  );
}
