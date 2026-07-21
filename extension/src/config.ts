/**
 * Build-time + runtime config. The Clerk publishable key, sync host (dashboard
 * origin), and default core URL are injected by esbuild `define` (see
 * scripts/build.mjs) so no secrets live in source. The core URL is also
 * overridable at runtime via chrome.storage (options), replacing the old
 * hardcoded constant in worker.ts.
 */

declare const __CLERK_PUBLISHABLE_KEY__: string;
declare const __SYNC_HOST__: string;
declare const __DEFAULT_CORE_URL__: string;

export const CLERK_PUBLISHABLE_KEY = __CLERK_PUBLISHABLE_KEY__;
export const SYNC_HOST = __SYNC_HOST__;

/** Detection-core base URL: chrome.storage override, else the baked default. */
export async function getCoreUrl(): Promise<string> {
  const { coreUrl } = await chrome.storage.local.get('coreUrl');
  return typeof coreUrl === 'string' && coreUrl ? coreUrl : __DEFAULT_CORE_URL__;
}
