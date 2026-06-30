// packages/core/lib/payments.ts

import { apiClient } from "./api";
import type { PlanSlug } from "./products";

interface CheckoutResponse {
  checkout_url: string;
}

type PaidPlanSlug = Extract<PlanSlug, "pro" | "team">;

export async function createCheckoutSession(appName: string, plan: PaidPlanSlug = "pro"): Promise<string> {
  const { data } = await apiClient.post<CheckoutResponse>("/polar/checkout", {
    app_name: appName,
    plan,
  });
  return data.checkout_url;
}

export async function redirectToCheckout(appName: string, plan: PaidPlanSlug = "pro"): Promise<void> {
  const url = await createCheckoutSession(appName, plan);
  if (typeof window !== "undefined") {
    window.location.href = url;
  }
}
