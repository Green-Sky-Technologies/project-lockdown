/**
 * Clerk client factory — SYNC HOST mode.
 *
 * The extension does NOT sign the user in itself (an in-extension OAuth redirect
 * to chrome-extension:// is rejected by providers). Instead it *syncs* the
 * session from the dashboard web app (the `syncHost`): the user signs in there
 * over https, and the extension's background client inherits that session and
 * mints backend-verifiable tokens via `clerk.session.getToken()`.
 *
 * Requirements (see manifest.json + Clerk Dashboard):
 *  - `host_permissions` must include the syncHost origin and the Clerk frontend
 *    API (`*.clerk.accounts.dev`), plus the `cookies` permission.
 *  - `chrome-extension://<id>` must be in the instance's `allowed_origins`.
 */
import { createClerkClient } from '@clerk/chrome-extension/client';

import { CLERK_PUBLISHABLE_KEY, SYNC_HOST } from '../config';

/**
 * Background client for the worker + popup reads (no UI). `syncHost` points it at
 * the dashboard so it borrows that session; `background: true` runs it in the
 * service-worker context. Cached so repeated calls share one client.
 */
type BackgroundClerk = Awaited<ReturnType<typeof createClerkClient>>;
let bgClientPromise: Promise<BackgroundClerk> | null = null;

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
