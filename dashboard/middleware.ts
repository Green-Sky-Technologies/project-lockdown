import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

// The dashboard is also the Clerk **sync host** for the extension (the extension
// syncs its auth state from this origin), so Clerk middleware must run here.
const isProtected = createRouteMatcher(['/activity(.*)', '/devices(.*)', '/settings(.*)']);

// Dev-only design preview: LOCKDOWN_PREVIEW=1 lets the screens render with
// sample data (lib/sample.ts) without a session. Ignored in production builds.
const preview = process.env.LOCKDOWN_PREVIEW === '1' && process.env.NODE_ENV !== 'production';

export default clerkMiddleware(async (auth, req) => {
  if (isProtected(req) && !preview) await auth.protect();
});

export const config = {
  matcher: [
    // Skip Next internals and static files; run on everything else + API routes.
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
    // Clerk auto-proxy path (handshake / account portal) — keep after api/trpc.
    '/__clerk/:path*',
  ],
};
