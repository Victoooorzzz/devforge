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
        </div>
      </div>
    </section>
  );
}
