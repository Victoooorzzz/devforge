// packages/core/index.ts
export { setToken, getToken, removeToken, isAuthenticated, fetchWithAuth } from "./lib/auth";
export { apiClient, uploadFile } from "./lib/api";
export { createCheckoutSession, createPortalSession, redirectToCheckout, redirectToPortal } from "./lib/stripe";
export { trackEvent, PlausibleScript } from "./lib/analytics";
export { generateMetadata, generateSoftwareAppJsonLd, generateOrganizationJsonLd } from "./lib/seo";
