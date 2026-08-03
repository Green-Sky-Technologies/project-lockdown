'use server';

import { revalidatePath } from 'next/cache';
import { createDeviceToken, revokeDeviceToken } from '@/lib/core';

/** Mint a token and hand the plaintext back to the client for its one-time reveal. */
export async function createTokenAction(name: string): Promise<{ token: string }> {
  const created = await createDeviceToken((name ?? '').trim().slice(0, 120));
  revalidatePath('/settings');
  return { token: created.token };
}

export async function revokeTokenAction(id: string): Promise<void> {
  await revokeDeviceToken(id);
  revalidatePath('/settings');
}
