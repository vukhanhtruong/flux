// Shared constants across the app
const cfg = (window as any).__FLUX_CONFIG__ || {};
export const USER_ID = cfg.VITE_USER_ID || import.meta.env.VITE_USER_ID || "need-onboarding";
export const SHOW_PROMO_CARD = import.meta.env.VITE_SHOW_PROMO_CARD !== "false";
