export { setToken, getToken, removeToken, isAuthenticated, fetchWithAuth, login, register, verify } from "./lib/auth";
export { apiClient, downloadFile, getApiBaseUrl, getApiUrl, uploadAndDownloadFile, uploadFile } from "./lib/api";
export { createCheckoutSession, redirectToCheckout } from "./lib/payments";
export {
  DEVFORGE_PRODUCTS,
  DEVFORGE_SUITE,
  PLAN_ORDER,
  getProduct,
  getProductByDomain,
} from "./lib/products";
export type {
  DevForgeProduct,
  FeatureComparisonRow,
  PlanSlug,
  ProductFAQ,
  ProductPlan,
  ProductSlug,
} from "./lib/products";

export { trackEvent, PlausibleScript } from "./lib/analytics";
export { generateMetadata, generateSoftwareAppJsonLd, generateOrganizationJsonLd } from "./lib/seo";
export { buildProductLlmsTxt, buildSuiteLlmsTxt } from "./lib/geo";

import { setToken, getToken, removeToken, isAuthenticated, fetchWithAuth, login, register, verify } from "./lib/auth";

export const auth = {
  setToken,
  getToken,
  removeToken,
  logout: removeToken,
  isAuthenticated,
  fetchWithAuth,
  login,
  register,
  verify
};
