/**
 * Stub for @clerk/chrome-extension in DEV_SKIP_AUTH builds. esbuild aliases the
 * real Clerk package to this file so the ~5MB SDK is excluded from dev bundles.
 * Nothing here is ever called at runtime — the dev code paths that would use
 * Clerk are guarded by `if (__DEV_SKIP_AUTH__)` and return first.
 */
export function createClerkClient(): never {
  throw new Error('Clerk is stubbed out in a DEV_SKIP_AUTH build');
}
