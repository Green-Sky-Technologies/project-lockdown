/**
 * Clerk client factories — STANDALONE session (no sync host).
 *
 * The extension holds its own Clerk session in chrome.storage (shared across the
 * popup, background worker, and the sign-in page). Sign-in happens on a full
 * extension PAGE (stable DOM that survives the OAuth redirect), configured via
 * clerk.load() with `allowedRedirectProtocols: ['chrome-extension:']` so the
 * post-OAuth redirect returns to the extension.
 */
import { createClerkClient } from '@clerk/chrome-extension/client';

import { CLERK_PUBLISHABLE_KEY } from '../config';

/** The extension's own full-page sign-in URL (a chrome-extension:// page). */
export function signinPageUrl(): string {
  return chrome.runtime.getURL('signin.html');
}

/**
 * Full DOM client for the sign-in PAGE. Loads with extension redirect config so
 * OAuth (Google, etc.) returns to the extension instead of a web origin.
 */
export async function getPageClerk() {
  const clerk = createClerkClient({ publishableKey: CLERK_PUBLISHABLE_KEY });
  const url = signinPageUrl();
  await clerk.load({
    allowedRedirectProtocols: ['chrome-extension:'],
    signInForceRedirectUrl: url,
    signUpForceRedirectUrl: url,
    afterSignOutUrl: url,
  });
  return clerk;
}

/**
 * Background client for the worker + popup reads (no UI). Shares the session
 * (chrome.storage) with the sign-in page and refreshes the session token.
 */
type BackgroundClerk = Awaited<ReturnType<typeof createClerkClient>>;
let bgClientPromise: Promise<BackgroundClerk> | null = null;

export function getBackgroundClerk(): Promise<BackgroundClerk> {
  if (!bgClientPromise) {
    bgClientPromise = createClerkClient({
      publishableKey: CLERK_PUBLISHABLE_KEY,
      background: true,
    });
  }
  return bgClientPromise;
}
