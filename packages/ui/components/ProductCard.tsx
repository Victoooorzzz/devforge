// packages/ui/components/ProductCard.tsx
import React from "react";

export interface ProductInfo {
  name: string;
  tagline: string;
  domain: string;
  accentColor: string;
  price: number;
  status: "live" | "beta" | "coming-soon";
}

interface ProductCardProps {
  product: ProductInfo;
}

const statusLabels: Record<ProductInfo["status"], string> = {
  live: "Live",
  beta: "Beta",
  "coming-soon": "Coming Soon",
};

export function ProductCard({ product }: ProductCardProps) {
  return (
    <a
      href={`https://${product.domain}`}
      target="_blank"
      rel="noopener noreferrer"
      className="group block p-6 rounded-lg transition-all duration-300 hover:translate-y-[-2px]"
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
                  ? `${product.accentColor}20`
                  : "rgba(163,163,163,0.15)",
            color:
              product.status === "live"
                ? "#10B981"
                : product.status === "beta"
                  ? product.accentColor
                  : "var(--color-text-secondary)",
          }}
        >
          {statusLabels[product.status]}
        </span>
      </div>

      <h3
        className="text-lg font-semibold mb-1"
        style={{ color: "var(--color-text)" }}
      >
        {product.name}
      </h3>
      <p
        className="text-sm mb-4"
        style={{ color: "var(--color-text-secondary)" }}
      >
        {product.tagline}
      </p>

      <div className="flex items-center justify-between">
        <span
          className="text-sm font-mono font-semibold"
          style={{ color: product.accentColor }}
        >
          ${product.price}/mo
        </span>
        <span
          className="text-xs"
          style={{ color: "var(--color-text-secondary)" }}
        >
          {product.domain}
        </span>
      </div>
    </a>
  );
}
