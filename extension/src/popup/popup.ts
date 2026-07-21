/**
 * Popup sign-in UI (vanilla). Signed out → a Clerk sign-in button; signed in →
 * the Clerk UserButton + an "active" status. Auth state syncs from the dashboard
 * (the Clerk sync host), so a session established there is picked up here.
 */
import { getPopupClerk } from '../auth/clerk-client';

const $ = (id: string) => document.getElementById(id)!;

async function main() {
  const status = $('status');
  let clerk;
  try {
    clerk = await getPopupClerk();
  } catch (e) {
    status.textContent = 'Could not initialize sign-in. Check the extension config.';
    // eslint-disable-next-line no-console
    console.error('[lockdown] clerk init failed', e);
    return;
  }

  const render = () => {
    const signedIn = !!clerk.user;
    $('signed-out').hidden = signedIn;
    $('signed-in').hidden = !signedIn;
    status.textContent = signedIn
      ? 'Monitoring active on this device.'
      : 'Signed out — monitoring is paused until you sign in.';
    if (signedIn) {
      const mount = $('user') as HTMLDivElement;
      mount.replaceChildren();
      clerk.mountUserButton(mount);
    }
  };

  $('signin').addEventListener('click', () => clerk.openSignIn());
  clerk.addListener(render); // re-render on auth changes
  render();
}

main();
