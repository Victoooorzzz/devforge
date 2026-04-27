export { setToken, getToken, removeToken, isAuthenticated, fetchWithAuth } from "./lib/auth";
export { apiClient, uploadFile } from "./lib/api";
export { createCheckoutSession, redirectToCheckout } from "./lib/payments";

export { trackEvent, PlausibleScript } from "./lib/analytics";
export { generateMetadata, generateSoftwareAppJsonLd, generateOrganizationJsonLd } from "./lib/seo";

import { setToken, getToken, removeToken, isAuthenticated, fetchWithAuth } from "./lib/auth";

export const auth = {
  setToken,
  getToken,
  removeToken,
  logout: removeToken,
  isAuthenticated,
  fetchWithAuth
};
