// packages/core/lib/payments.ts

import { apiClient } from "./api";

interface CheckoutResponse {
  checkout_url: string;
}

export async function createCheckoutSession(appName: string): Promise<string> {
  const { data } = await apiClient.post<CheckoutResponse>("/polar/checkout", {
    app_name: appName,
  });
  return data.checkout_url;
}

export async function redirectToCheckout(appName: string): Promise<void> {
  const url = await createCheckoutSession(appName);
  if (typeof window !== "undefined") {
    window.location.href = url;
  }
}
