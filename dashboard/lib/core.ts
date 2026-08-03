import { auth } from '@clerk/nextjs/server';

/**
 * Server-side calls to the detection core's authenticated endpoints, carrying the
 * signed-in parent's Clerk session token. This runs only on the server (never in
 * the browser), so the token never touches the client and there is no CORS hop.
 *
 * The core owns all device-token logic (mint/hash/validate); the dashboard is a
 * thin UI over it.
 */

const CORE_URL = (process.env.CORE_URL ?? 'https://project-lockdown-production.up.railway.app').replace(
  /\/$/,
  '',
);

export interface DeviceToken {
  id: string;
  name: string;
  created_at: string;
  last_used_at: string | null;
  revoked: boolean;
}

export interface CreatedDeviceToken extends DeviceToken {
  token: string; // plaintext — returned once, at creation
}

async function coreFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) throw new Error('not signed in');
  return fetch(`${CORE_URL}${path}`, {
    ...init,
    headers: {
      ...(init.headers ?? {}),
      'content-type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    cache: 'no-store',
  });
}

export async function listDeviceTokens(): Promise<DeviceToken[]> {
  const r = await coreFetch('/device-tokens');
  if (!r.ok) throw new Error(`core ${r.status} listing device tokens`);
  return (await r.json()) as DeviceToken[];
}

export async function createDeviceToken(name: string): Promise<CreatedDeviceToken> {
  const r = await coreFetch('/device-tokens', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
  if (!r.ok) throw new Error(`core ${r.status} creating device token`);
  return (await r.json()) as CreatedDeviceToken;
}

export async function revokeDeviceToken(id: string): Promise<void> {
  const r = await coreFetch(`/device-tokens/${id}`, { method: 'DELETE' });
  if (!r.ok && r.status !== 204) throw new Error(`core ${r.status} revoking device token`);
}
