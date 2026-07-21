/**
 * Session token retrieval for the service worker. Returns a backend-verifiable
 * Clerk session JWT, or null when signed out.
 */
import { getBackgroundClerk } from './clerk-client';

export async function getSessionToken(): Promise<string | null> {
  try {
    const clerk = await getBackgroundClerk();
    const token = await clerk.session?.getToken();
    return token ?? null;
  } catch {
    return null; // treat any failure as signed-out; worker surfaces needsSignIn
  }
}
