/**
 * Session token retrieval for the service worker. Returns a backend-verifiable
 * Clerk session JWT, or null when signed out.
 */
import { getBackgroundClerk } from './clerk-client';

export async function getSessionToken(): Promise<string | null> {
  try {
    const clerk = await getBackgroundClerk();
    // The background client may resolve before the sync-host session has
    // propagated from the dashboard. If it's loaded but has no session yet,
    // give the sync a brief beat before giving up.
    if (clerk.loaded && !clerk.session) {
      await new Promise((r) => setTimeout(r, 400));
    }
    const token = await clerk.session?.getToken();
    return token ?? null;
  } catch {
    return null; // treat any failure as signed-out; worker surfaces needsSignIn
  }
}
