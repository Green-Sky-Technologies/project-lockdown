'use server';

import { revalidatePath } from 'next/cache';
import { updateNotificationSettings } from '@/lib/core';

export async function setNotificationChannelAction(
  channel: 'dashboard_only' | 'email',
): Promise<void> {
  await updateNotificationSettings(channel);
  revalidatePath('/settings');
}
