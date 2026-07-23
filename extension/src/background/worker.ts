/**
 * Background service worker: the ONLY component that talks to the detection core.
 * Content scripts hand it a ClassifyRequest; it attaches the signed-in user's
 * Clerk session token and POSTs to the core.
 *
 * DEV bypass: when built with DEV_SKIP_AUTH=1, the worker skips sign-in entirely
 * and never imports Clerk — so background.js stays tiny (no 5.4MB Clerk SDK in
 * the service worker) and there's nothing to crash-loop on reload. Pair with the
 * core's LOCKDOWN_REQUIRE_AUTH=false. Production builds (flag off) require auth.
 */
import type { ClassifyRequest, Verdict } from '../contract/verdict';
import { getCoreUrl } from '../config';

// Replaced at build time by esbuild `define`. `if (__DEV_SKIP_AUTH__)` branches
// are dead-code-eliminated in the build that doesn't match, so the Clerk dynamic
// import below is dropped entirely from a dev build.
declare const __DEV_SKIP_AUTH__: boolean;

interface ClassifyMessage {
  type: 'classify';
  payload: ClassifyRequest;
}

interface ClassifyResponse {
  ok: boolean;
  verdict?: Verdict;
  error?: string;
  needsSignIn?: boolean;
}

async function getToken(): Promise<string | null> {
  if (__DEV_SKIP_AUTH__) return null;
  const { getSessionToken } = await import('../auth/token');
  return getSessionToken();
}

async function classify(payload: ClassifyRequest): Promise<ClassifyResponse> {
  const token = await getToken();
  if (!token && !__DEV_SKIP_AUTH__) return { ok: false, needsSignIn: true };

  const coreUrl = await getCoreUrl();
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const r = await fetch(`${coreUrl}/classify`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });
    if (r.status === 401) return { ok: false, needsSignIn: true };
    if (!r.ok) return { ok: false, error: `core ${r.status}` };
    return { ok: true, verdict: (await r.json()) as Verdict };
  } catch (e: unknown) {
    return { ok: false, error: String(e) };
  }
}

chrome.runtime.onMessage.addListener((msg: ClassifyMessage, _sender, sendResponse) => {
  if (msg?.type !== 'classify') return undefined;
  classify(msg.payload).then(sendResponse);
  return true; // keep the message channel open for the async response
});
