/**
 * Build-time + runtime config.
 *
 * Auth is a **device token** (a `pld_live_…` personal-access-token the parent
 * generates in the dashboard and pastes into the popup). It lives in
 * chrome.storage and is sent as a Bearer token to the core — no Clerk, no
 * cookies, no sync host in the extension. The default core URL and the dashboard
 * URL (for the "get a token" link) are injected by esbuild `define`; the core URL
 * is overridable at runtime via chrome.storage.
 */

declare const __DEFAULT_CORE_URL__: string;
declare const __DASHBOARD_URL__: string;

/** Where the parent generates/manages device tokens. */
export function settingsUrl(): string {
  return `${__DASHBOARD_URL__.replace(/\/$/, '')}/settings`;
}

/** Detection-core base URL: chrome.storage override, else the baked default. */
export async function getCoreUrl(): Promise<string> {
  const { coreUrl } = await chrome.storage.local.get('coreUrl');
  return typeof coreUrl === 'string' && coreUrl ? coreUrl : __DEFAULT_CORE_URL__;
}

// --- Device token (the extension's only credential) --------------------------
const TOKEN_KEY = 'deviceToken';

export async function getDeviceToken(): Promise<string | null> {
  const { [TOKEN_KEY]: t } = await chrome.storage.local.get(TOKEN_KEY);
  return typeof t === 'string' && t ? t : null;
}

export async function setDeviceToken(token: string): Promise<void> {
  await chrome.storage.local.set({ [TOKEN_KEY]: token.trim() });
}

export async function clearDeviceToken(): Promise<void> {
  await chrome.storage.local.remove(TOKEN_KEY);
}
