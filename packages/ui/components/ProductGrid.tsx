// packages/ui/components/ProductGrid.tsx
import React from "react";
import { ProductCard, type ProductInfo } from "./ProductCard";

interface ProductGridProps {
  products: ProductInfo[];
  title?: string;
  subtitle?: string;
}

export function ProductGrid({
  products,
  title = "Our Products",
  subtitle,
}: ProductGridProps) {
  const needsPlaceholder = products.length % 3 === 2;

  return (
    <section className="py-20 md:py-28">
      <div className="section-container">
        <div className="text-center mb-16">
          <h2 className="heading-section text-3xl md:text-4xl mb-4">
            {title}
          </h2>
          {subtitle && (
            <p
              className="text-lg max-w-2xl mx-auto"
              style={{ color: "var(--color-text-secondary)" }}
            >
              {subtitle}
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {products.map((product) => (
            <ProductCard key={product.domain} product={product} />
          ))}
          {needsPlaceholder ? (
            <div className="product-suite-card flex min-h-[24rem] flex-col justify-between rounded-lg border border-dashed border-white/10 p-6">
              <div>
                <div className="mb-5 flex h-10 w-10 items-center justify-center rounded-lg border border-white/10 text-lg" style={{ color: "var(--color-text-secondary)" }}>
                  +
                </div>
                <h3 className="mb-2 text-lg font-semibold leading-tight" style={{ color: "var(--color-text)" }}>
                  More tools coming soon
                </h3>
                <p className="text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                  The suite stays focused: small developer tools that remove repetitive operational work.
                </p>
              </div>
              <span className="mt-6 inline-flex w-fit rounded-md border border-white/10 px-3 py-2 text-xs font-semibold" style={{ color: "var(--color-text-secondary)" }}>
                Watch roadmap
              </span>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
