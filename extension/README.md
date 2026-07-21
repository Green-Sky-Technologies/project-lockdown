# Capture extension (Chromium MV3)

Thin, swappable capture front-end (design doc §3). It observes the chatbot input
and rendered turns, runs the **local recall gate**, POSTs flagged windows to the
detection core, and renders the **lock overlay** on verdicts that cross the lock
threshold. It knows nothing about classification — that lives in the core.

Scoped to specific chatbot domains only (**not** `<all_urls>`) to keep the
install prompt and permission footprint minimal.

## Build

```bash
cd extension
npm install
npm run build      # syncs the wordlist from core, bundles into dist/
```

Then load it: `chrome://extensions` → enable Developer mode → **Load unpacked** →
select `extension/dist`.

Run the core first (`cd core && … uvicorn lockdown_core.app:app`) so the
background worker can reach `http://localhost:8000/classify`.

### Auth build (Clerk)

The worker attaches a Clerk session token to every `/classify` call; the popup
handles sign-in. Bake your config in at build time:

```bash
CLERK_PUBLISHABLE_KEY='pk_…' \
SYNC_HOST='https://your-dashboard.vercel.app' \
DEFAULT_CORE_URL='https://your-core.example.com' \
  npm run build
```

The manifest pins a `"key"`, so the extension ID is stable:
`deocaekmmjagaicbdckdpnhjpebbooch` — register `chrome-extension://deocaekmmjagaicbdckdpnhjpebbooch`
in Clerk (allowed origins) and the core (`LOCKDOWN_CLERK_AUTHORIZED_PARTIES`).
Full sequence in the repo-root **`DEPLOY.md`**. For local dev, run the core with
`LOCKDOWN_REQUIRE_AUTH=false` to skip sign-in.

## Try it

Open one of the monitored hosts (chatgpt.com, claude.ai, gemini.google.com) and
send a message containing a wordlist term with real-target framing (e.g. a threat
toward a named person). The recall gate fires, the core classifies, and the lock
overlay appears. A benign message never leaves the page.

## Layout

| Path | Responsibility |
|---|---|
| `manifest.json` | MV3 manifest; scoped `host_permissions` |
| `src/hosts/registry.ts` + `hosts/*.ts` | Per-host adapter configs — hosts are data |
| `src/content/observer.ts` | DOM capture (send events + assistant-turn scrape) |
| `src/content/window.ts` | Client-side rolling window |
| `src/content/recall.ts` | Local recall gate (wordlist synced from core at build) |
| `src/content/overlay.ts` | Lock overlay UI |
| `src/background/worker.ts` | POSTs to the core; only component that talks to it |
| `src/contract/verdict.ts` | TS mirror of the verdict contract |
| `src/generated/wordlist.ts` | Generated from `core/.../wordlist/violence_to_others.txt` |
