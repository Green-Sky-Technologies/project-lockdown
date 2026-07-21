# Dashboard

A minimal, read-only web app where an adult signs in (Clerk) and reviews the
conversations Project Lockdown flagged for them. It reads verdicts from Neon,
strictly scoped to the signed-in account — there is no raw message text stored or
shown, only the flag metadata + offset spans.

**It also serves as the Clerk _sync host_** for the browser extension: the
extension can't hold its own Clerk session origin, so it syncs auth state from
this app. One Clerk instance powers both.

## Stack
- Next.js (App Router) + `@clerk/nextjs` (auth, `clerkMiddleware`, `auth()`).
- `@neondatabase/serverless` HTTP driver — ideal for Vercel serverless.
- Every query scoped by `auth()` (`userId` / `orgId`); ownership enforced in the query, never by trusting a URL id.

## Run locally
```bash
cd dashboard
npm install
cp .env.example .env.local   # add Clerk keys + the SAME Neon DATABASE_URL the core uses
npm run dev                  # http://localhost:3000
```
Sign in, then visit `/verdicts`. Rows appear once the core has persisted flagged
verdicts for your account (see `core/` — run it with auth on and classify a
threat as the signed-in user).

## Deploy to Vercel
Auto-detected (Next.js). Set `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`,
and `DATABASE_URL` in the Vercel project. After deploy:
1. In Clerk, add this app's domain as an allowed origin, and configure it as the extension's sync host.
2. Put this app's origin into the core's `LOCKDOWN_CLERK_AUTHORIZED_PARTIES` (+ CORS) and the extension's manifest/host_permissions.

## Pages
- `/` — landing + sign-in.
- `/verdicts` — this account's flagged verdicts (list).
- `/verdicts/[id]` — detail (rationale/evidence hideable via `NEXT_PUBLIC_SHOW_RATIONALE=false`, per design doc §11.2).
