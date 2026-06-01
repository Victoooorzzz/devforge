// packages/core/lib/payments.ts

import { apiClient } from "./api";

interface CheckoutResponse {
  checkout_url: string;
}

export async function createCheckoutSession(productId: string): Promise<string> {
  const { data } = await apiClient.post<CheckoutResponse>("/polar/checkout", {
    product_id: productId,
  });
  return data.checkout_url;
}

export async function redirectToCheckout(productId: string): Promise<void> {
  const url = await createCheckoutSession(productId);
  if (typeof window !== "undefined") {
    window.location.href = url;
  }
}
