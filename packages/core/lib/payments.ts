// packages/core/lib/payments.ts

import { apiClient } from "./api";

interface CheckoutResponse {
  checkout_url: string;
}

export async function createCheckoutSession(variantId: string): Promise<string> {
  const { data } = await apiClient.post<CheckoutResponse>("/lemonsqueezy/checkout", {
    variant_id: variantId,
  });
  return data.checkout_url;
}

export async function redirectToCheckout(variantId: string): Promise<void> {
  const url = await createCheckoutSession(variantId);
  if (typeof window !== "undefined") {
    window.location.href = url;
  }
}

