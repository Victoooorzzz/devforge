// packages/core/lib/stripe.ts

import { apiClient } from "./api";

interface CheckoutResponse {
  checkout_url: string;
}

interface PortalResponse {
  portal_url: string;
}

export async function createCheckoutSession(priceId: string): Promise<string> {
  const { data } = await apiClient.post<CheckoutResponse>("/stripe/checkout", {
    price_id: priceId,
  });
  return data.checkout_url;
}

export async function createPortalSession(): Promise<string> {
  const { data } = await apiClient.post<PortalResponse>("/stripe/portal");
  return data.portal_url;
}

export async function redirectToCheckout(priceId: string): Promise<void> {
  const url = await createCheckoutSession(priceId);
  if (typeof window !== "undefined") {
    window.location.href = url;
  }
}

export async function redirectToPortal(): Promise<void> {
  const url = await createPortalSession();
  if (typeof window !== "undefined") {
    window.location.href = url;
  }
}
