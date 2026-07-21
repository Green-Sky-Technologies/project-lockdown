# Mock chatbot test harness

A static, deployable page that **mimics the interfaces of ChatGPT, Claude, and
Gemini** so you (and other testers) can exercise the Project Lockdown extension
end-to-end without visiting the real sites. There is **no AI model** — on send it
appends a canned assistant reply. Its real job is to reproduce the exact DOM
hooks each extension adapter listens for, so the **real** capture → recall gate →
core → lock overlay pipeline runs.

## How it maps to the extension

Each host mode reproduces the selectors in the matching adapter under
`extension/src/hosts/`:

| Mode | Composer | Send button | Turn hooks |
|---|---|---|---|
| ChatGPT (`chatgpt.ts`) | `#prompt-textarea` (contenteditable) | `button[data-testid="send-button"]` | `[data-message-author-role="user"\|"assistant"]` |
| Claude (`claude.ts`) | `div.ProseMirror[contenteditable]` | `button[aria-label="Send message"]` | `[data-testid="user-message"]` / `[data-testid="assistant-message"].font-claude-message` |
| Gemini (`gemini.ts`) | `rich-textarea div[contenteditable][role="textbox"]` | `button[aria-label="Send message"]` | `<user-query>` / `<model-response>` |

The mode is chosen with `?host=chatgpt.com|claude.ai|gemini.google.com` (the host
switcher navigates there and reloads). The page advertises its mode via
`document.documentElement.dataset.lockdownEmulate`, which the extension reads to
pick the right adapter on a non-real origin (see the resolver in
`extension/src/content/index.ts`).

This is a **Vite** project — `npm run dev` for a hot-reloading dev server, `npm
run build` for a static `dist/` that Vercel's zero-config Vite preset serves.

## Run locally

```bash
# from repo root: build + load the extension first
cd extension && npm run build          # then load extension/dist unpacked at chrome://extensions
cd ../core && LOCKDOWN_USE_FAKE_CLASSIFIER=1 uv run uvicorn lockdown_core.app:app   # the detection core on :8000

# dev server for this site
cd ../test-site && npm install && npm run dev
# open the printed URL, e.g. http://localhost:5173/?host=chatgpt.com
```

The extension manifest whitelists `http://localhost/*` (match patterns ignore the
port, so any Vite dev port is covered), so the content script injects here. The
background worker calls the core at `http://localhost:8000` — keep the core
running or you'll get no verdict.

To preview the production build locally: `npm run build && npm run preview`.

## Deploy to Vercel

Vercel auto-detects the Vite framework (build `vite build`, output `dist/`) — no
`vercel.json` needed. Set **`test-site/` as the project root**.

```bash
cd test-site
vercel            # first run links the project; pick test-site as the root dir
vercel --prod
```

Then pin the deployed origin in **`extension/manifest.json`** — replace
`https://project-lockdown-test.vercel.app/*` (in both `content_scripts[0].matches`
and `host_permissions`) with your real domain — and rebuild:

```bash
cd ../extension && npm run build   # reload the unpacked extension afterwards
```

> Testers loading the extension must also have a **core** reachable. Running it
> locally on `:8000` works even from the https Vercel page (the fetch originates
> from the extension's service worker, not the page, so it isn't blocked as mixed
> content). To avoid every tester running the core, deploy the core and update
> `CORE_URL` in `extension/src/background/worker.ts`.

## Try it

1. Open the page, pick a host with the switcher.
2. Send a benign message → canned reply, **no lock**.
3. Send a message containing a wordlist term with real-target framing (e.g. a
   threat toward a named person) → the recall gate fires, the core classifies,
   and the **lock overlay** appears.
