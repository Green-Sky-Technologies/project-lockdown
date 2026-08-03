import { auth } from '@clerk/nextjs/server';
import { listDeviceTokens, type DeviceToken } from '@/lib/core';
import { DeviceTokens } from './DeviceTokens';

// Live per-request, scoped to the signed-in parent — never prerender.
export const dynamic = 'force-dynamic';

export default async function SettingsPage() {
  const { userId } = await auth();
  if (!userId) return null; // middleware protects this route; guard for types.

  let tokens: DeviceToken[] = [];
  let error: string | null = null;
  try {
    tokens = await listDeviceTokens();
  } catch {
    error = 'Could not reach the detection service. Try again in a moment.';
  }

  return (
    <section>
      <h1>Extension setup</h1>
      <p className="muted">
        Generate a device token, then paste it into the Project Lockdown browser
        extension (its popup → “Connect”). The token keeps the extension signed in
        for as long as you like — revoke it here at any time to disconnect that
        device instantly.
      </p>
      {error ? (
        <p className="empty">{error}</p>
      ) : (
        <DeviceTokens initial={tokens} />
      )}
    </section>
  );
}
