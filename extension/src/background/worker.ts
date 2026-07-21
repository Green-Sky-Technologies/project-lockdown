/**
 * Background service worker: the ONLY component that talks to the detection core.
 * Content scripts hand it a ClassifyRequest; it attaches the signed-in user's
 * Clerk session token and POSTs to the core. No token / a 401 → `needsSignIn`, so
 * the content script can prompt the adult to sign in via the popup.
 */
import type { ClassifyRequest, Verdict } from '../contract/verdict';
import { getSessionToken } from '../auth/token';
import { getCoreUrl } from '../config';

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

async function classify(payload: ClassifyRequest): Promise<ClassifyResponse> {
  const token = await getSessionToken();
  if (!token) return { ok: false, needsSignIn: true };

  const coreUrl = await getCoreUrl();
  try {
    const r = await fetch(`${coreUrl}/classify`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
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
