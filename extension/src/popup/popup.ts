/**
 * Popup UI (vanilla). Signed out → a button that opens sign-in on the DASHBOARD
 * (the Clerk sync host) in a new tab; the session then syncs back to the
 * extension automatically. Signed in → the Clerk UserButton + "active" status.
 *
 * We deliberately do NOT embed Clerk's SignIn card here: OAuth redirects inside a
 * small extension popup are fragile, and re-rendering a Clerk-managed (React) DOM
 * node on auth changes throws `removeChild` errors. The sync-host flow is the
 * robust, Clerk-recommended path for extensions.
 */
import { getPopupClerk } from '../auth/clerk-client';
import { SYNC_HOST } from '../config';

const $ = (id: string) => document.getElementById(id)!;

async function main() {
  const status = $('status');
  const signedOut = $('signed-out');
  const signedIn = $('signed-in');

  // Full popup client (has the UI mount methods; syncs session from the host).
  let clerk;
  try {
    clerk = await getPopupClerk();
  } catch (e) {
    status.textContent = 'Sign-in unavailable — check the extension config.';
    // eslint-disable-next-line no-console
    console.error('[lockdown] clerk init failed', e);
    return;
  }

  $('signin').addEventListener('click', () => {
    chrome.tabs.create({ url: `${SYNC_HOST}/sign-in` });
  });

  let userMounted = false; // mount the Clerk UserButton once; never re-render it
  const render = () => {
    const isIn = !!clerk.user;
    signedOut.hidden = isIn;
    signedIn.hidden = !isIn;
    status.textContent = isIn ? 'Monitoring active on this device.' : 'Sign in to enable monitoring.';
    status.classList.toggle('active', isIn);
    if (isIn && !userMounted) {
      clerk.mountUserButton($('user') as HTMLDivElement);
      userMounted = true;
    }
  };

  clerk.addListener(render); // reflect sync-host sign-in/out without a reload
  render();
}

main();
