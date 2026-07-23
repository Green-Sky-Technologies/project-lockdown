# Deploy runbook — auth, database, dashboard, extension

End-to-end setup for a protected deployment: Clerk (login), Neon (verdict store),
the core (FastAPI), the dashboard (Next.js on Vercel, also the Clerk sync host),
and the extension (Clerk login → Bearer token). Order matters — follow top to
bottom.

## Key fact: the extension ID is fixed
The extension manifest pins a `"key"`, so the extension ID is **stable**:

```
deocaekmmjagaicbdckdpnhjpebbooch
→ origin: chrome-extension://deocaekmmjagaicbdckdpnhjpebbooch
```

You'll register that origin with Clerk and the core below. (To use your own key,
regenerate with `openssl genrsa 2048 | openssl rsa -pubout -outform DER | base64`,
put it in `manifest.json` `"key"`, and re-derive the ID.)

## Secrets map — where each value comes from, and where it goes

> **Rule:** the committed `*.env.example` files are **placeholders only**. Real
> values go in the **gitignored** `.env` / `.env.local` files **and** in each
> host's env settings (Render/Railway Variables, Vercel Environment Variables).
> Never paste a real key or DB URL into a `.env.example`.

| Value | Get it from | Where it goes |
|---|---|---|
| **Clerk publishable key** (`pk_…`, not secret) | Clerk → API keys | Dashboard: `.env.local` + Vercel (`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`) · Extension: `extension/.env` (`CLERK_PUBLISHABLE_KEY`) |
| **Clerk secret key** (`sk_…`, SERVER-ONLY) | Clerk → API keys | Dashboard: `.env.local` + Vercel (`CLERK_SECRET_KEY`) · Core: host env (`CLERK_SECRET_KEY`). **Never in the extension.** |
| **Neon pooled `DATABASE_URL`** | Neon Console → Connection Details → **Pooled** (host has `-pooler`) | Core: host env (`DATABASE_URL`) · Dashboard: `.env.local` + Vercel (`DATABASE_URL`) · the `alembic upgrade` command |
| **Anthropic API key** | console.anthropic.com → API keys (also set a **spend cap**) | Core: host env (`ANTHROPIC_API_KEY`) |
| **LangSmith key** (optional) | smith.langchain.com → API keys | Core: host env (`LANGSMITH_API_KEY`) |
| Extension origin (config, fixed) | `chrome-extension://deocaekmmjagaicbdckdpnhjpebbooch` | Clerk allowed origins · Core `LOCKDOWN_CLERK_AUTHORIZED_PARTIES` + `LOCKDOWN_CORS_ALLOW_ORIGINS` |
| Dashboard origin (config) | your Vercel URL | Extension `SYNC_HOST` · Clerk sync host · Core authorized parties + CORS |
| Core URL (config) | your Render/Railway URL | Extension `DEFAULT_CORE_URL` |

Per-component templates: `core/.env.example`, `dashboard/.env.example`,
`extension/.env.example` — each annotated with the same get-it/put-it notes.

## 1. Neon (database)
1. Create a Neon project → copy the **pooled** connection string (host contains `-pooler`).
2. Run migrations from `core/` with that URL:
   ```bash
   DATABASE_URL='postgresql://…-pooler….neon.tech/db' uv run alembic upgrade head
   ```
   Creates `accounts` + `verdict_records`.

## 2. Clerk (identity)
1. Create a Clerk application. Note the **Publishable key** (`pk_…`) and **Secret key** (`sk_…`).
2. **Allowed origins** — add the extension origin: `chrome-extension://deocaekmmjagaicbdckdpnhjpebbooch`.
3. **Sync host** — configure the dashboard origin (below) as the extension's sync host (Clerk → the browser-extension settings). The dashboard and extension share this one Clerk instance.
4. Note your Clerk **Frontend API** host (e.g. `https://<slug>.clerk.accounts.dev`) — the extension manifest's `host_permissions` already allows `https://*.clerk.accounts.dev/*`; pin it to your exact slug for production.

## 3. Dashboard (Vercel — also the Clerk sync host)
1. Deploy `dashboard/` to Vercel (Next.js auto-detected). Set env:
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`
   - `DATABASE_URL` (same Neon pooled string)
   - *(optional)* `NEXT_PUBLIC_SHOW_RATIONALE=false` to hide model rationale/evidence pending counsel sign-off (§11.2)
2. Note the deployed origin, e.g. `https://lockdown-dash.vercel.app`. Set it as the Clerk sync host (step 2.3).

## 4. Core (persistent host — Render / Railway)
Deploy `core/` as a **persistent web service** (not serverless — the real
classifier makes multi-second LLM calls). Build `pip install .`, start
`uvicorn lockdown_core.app:app --host 0.0.0.0 --port $PORT`. Env:
- `ANTHROPIC_API_KEY` — and set a **spend cap + usage alert in the Anthropic Console** (billing → limits). This is the dollar backstop; the per-account rate limit is the call backstop.
- `LOCKDOWN_REQUIRE_AUTH=true`
- `CLERK_SECRET_KEY`
- `LOCKDOWN_CLERK_AUTHORIZED_PARTIES=chrome-extension://deocaekmmjagaicbdckdpnhjpebbooch,https://lockdown-dash.vercel.app`
- `DATABASE_URL` (same Neon pooled string), `LOCKDOWN_PERSIST_VERDICTS=true`
- `LOCKDOWN_CORS_ALLOW_ORIGINS=chrome-extension://deocaekmmjagaicbdckdpnhjpebbooch,https://lockdown-dash.vercel.app`
- *(tune)* `LOCKDOWN_RATE_LIMIT_PER_MINUTE`, `LOCKDOWN_RATE_LIMIT_BURST`

Note the deployed core URL, e.g. `https://lockdown-core.onrender.com`.

## 5. Extension (build with your config, then load/publish)
Build with your Clerk key + origins baked in:
```bash
cd extension
CLERK_PUBLISHABLE_KEY='pk_…' \
SYNC_HOST='https://lockdown-dash.vercel.app' \
DEFAULT_CORE_URL='https://lockdown-core.onrender.com' \
  npm run build
```
Load `extension/dist` unpacked (or package it). Because the manifest pins `"key"`,
the ID stays `deocaekmmjagaicbdckdpnhjpebbooch` on every machine. Add the deployed
core origin to `manifest.json` `host_permissions` if it isn't `*.onrender.com`-style
already covered, and rebuild.

## 6. Verify end-to-end
1. Open the dashboard, sign in with Clerk.
2. Open the extension popup → **Sign in** (syncs the session from the dashboard host) → shows "Monitoring active".
3. Visit a monitored chatbot (or the mock test site) → send a message that trips the recall gate with real-target framing → the worker attaches the Bearer token → the core classifies + persists → the **lock overlay** appears.
4. Back in the dashboard → `/verdicts` shows the flagged row (attributed to your account).
5. Sign out in the popup → the worker gets no token / a 401 → the content script logs a "sign in to enable monitoring" prompt and does not lock.

## Governance / retention (§8 / §11)
- Store **no raw text** (guaranteed by the contract) — the DB holds only flag metadata + offset spans.
- Only **lock/log** verdicts are persisted (never `NO_ACTION`).
- Retention is **policy, not code**: verdict rows have `retention_expires_at` (unset by default = kept). Once counsel sets a retention policy, populate that column on write and schedule the purge:
  ```bash
  python -m lockdown_core.persistence.retention   # deletes rows past retention_expires_at
  ```
- `LOCKDOWN_REQUIRE_AUTH=false` is **dev-only** — production must keep it true so every stored verdict is attributable (audit trail).

## Scaling notes
- The per-account rate limiter is **in-memory** (single instance). For multiple core instances, move it to a shared store (Redis / Neon) so limits are global.
- Clerk verification is networkless (JWKS cached ~5 min) — no per-request Clerk call.
