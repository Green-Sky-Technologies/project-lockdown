/**
 * Clerk client factories (SDK v3, vanilla / no-React path).
 *
 * - Background/service worker: `createClerkClient({ background: true })` (async).
 * - Popup: `createClerkClient({...})` (sync). Both sync auth state from the
 *   dashboard origin (`syncHost`) — an extension can't hold its own Clerk session
 *   origin, so it mirrors one from the companion web app.
 */
import { createClerkClient } from '@clerk/chrome-extension/client';

import { CLERK_PUBLISHABLE_KEY, SYNC_HOST } from '../config';

type BackgroundClerk = Awaited<ReturnType<typeof createClerkClient>>;

let bgClientPromise: Promise<BackgroundClerk> | null = null;

/** Cached background client for the service worker (keeps the token fresh). */
export function getBackgroundClerk(): Promise<BackgroundClerk> {
  if (!bgClientPromise) {
    bgClientPromise = createClerkClient({
      publishableKey: CLERK_PUBLISHABLE_KEY,
      syncHost: SYNC_HOST,
      background: true,
    });
  }
  return bgClientPromise;
}

/** A loaded popup client (DOM context). */
export async function getPopupClerk() {
  const clerk = createClerkClient({
    publishableKey: CLERK_PUBLISHABLE_KEY,
    syncHost: SYNC_HOST,
  });
  await clerk.load();
  return clerk;
}
