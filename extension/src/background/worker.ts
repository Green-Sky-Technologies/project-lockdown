/**
 * Background service worker: the ONLY component that talks to the detection core.
 * Content scripts hand it a ClassifyRequest; it attaches the parent's device token
 * (a `pld_live_…` Bearer credential from chrome.storage) and POSTs to the core.
 *
 * No Clerk, no sign-in flow, no bundled SDK — auth is just a stored string. If the
 * core is running with auth off (local dev) the request still works without a
 * token; if auth is on and the token is missing/invalid the core returns 401 and
 * we surface `needsSetup` so the popup prompts the parent to connect.
 */
import type { ClassifyRequest, Verdict } from '../contract/verdict';
import { getCoreUrl, getDeviceToken } from '../config';

interface ClassifyMessage {
  type: 'classify';
  payload: ClassifyRequest;
}

interface ClassifyResponse {
  ok: boolean;
  verdict?: Verdict;
  error?: string;
  needsSetup?: boolean;
}

async function classify(payload: ClassifyRequest): Promise<ClassifyResponse> {
  const token = await getDeviceToken();
  const coreUrl = await getCoreUrl();
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const r = await fetch(`${coreUrl}/classify`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });
    if (r.status === 401) return { ok: false, needsSetup: true };
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
