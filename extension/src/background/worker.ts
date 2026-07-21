/**
 * Background service worker: the ONLY component that talks to the detection core.
 * Content scripts hand it a ClassifyRequest; it POSTs to the core and returns the
 * verdict. Cross-origin fetch to the core requires the core origin in
 * host_permissions (see manifest.json).
 */
import type { ClassifyRequest, Verdict } from '../contract/verdict';

// Core endpoint. TODO: make configurable via chrome.storage / options page.
const CORE_URL = 'http://localhost:8000';

interface ClassifyMessage {
  type: 'classify';
  payload: ClassifyRequest;
}

chrome.runtime.onMessage.addListener((msg: ClassifyMessage, _sender, sendResponse) => {
  if (msg?.type !== 'classify') return undefined;

  fetch(`${CORE_URL}/classify`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(msg.payload),
  })
    .then((r) => {
      if (!r.ok) throw new Error(`core ${r.status}`);
      return r.json() as Promise<Verdict>;
    })
    .then((verdict) => sendResponse({ ok: true, verdict }))
    .catch((e: unknown) => sendResponse({ ok: false, error: String(e) }));

  return true; // keep the message channel open for the async response
});
