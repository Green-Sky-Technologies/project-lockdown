'use server';

import { auth } from '@clerk/nextjs/server';
import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { updateVerdictStatus } from '@/lib/db';

const ALLOWED = ['reviewed', 'snoozed', 'dismissed'] as const;
type ReviewStatus = (typeof ALLOWED)[number];

export async function setStatusAction(id: string, status: ReviewStatus): Promise<void> {
  if (!ALLOWED.includes(status)) throw new Error('bad status');
  const { userId, orgId } = await auth();
  if (!userId) throw new Error('not signed in');
  await updateVerdictStatus(id, userId, orgId ?? null, status);
  revalidatePath('/activity');
  revalidatePath('/');
  redirect('/activity');
}
