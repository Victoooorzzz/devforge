// apps/template/frontend/src/app/pricing-section.tsx
"use client";

import { PricingCard } from "@devforge/ui";
import { redirectToCheckout, trackEvent } from "@devforge/core";
import { product } from "@/config/product";

export function PricingSection() {
  const handleCheckout = async () => {
    trackEvent("checkout_started");
    await redirectToCheckout(product.pricing.lsVariantId);

  };

  return (
    <PricingCard
      planName={product.pricing.planName}
      price={product.pricing.price}
      description={product.pricing.description}
      features={product.pricing.features}
      onCheckout={handleCheckout}
    />
  );
}
