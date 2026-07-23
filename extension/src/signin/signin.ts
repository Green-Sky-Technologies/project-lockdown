/**
 * Full-page sign-in (opened in a tab). A stable DOM that survives the OAuth
 * redirect — unlike the popup. Mounts Clerk's SignIn when signed out; on success
 * the session is written to chrome.storage (shared with the worker), and we show
 * a "done" message. Guards against re-mounting so React never tears down a node
 * it doesn't own.
 */
import { getPageClerk } from '../auth/clerk-client';

const clerkEl = () => document.getElementById('clerk') as HTMLDivElement;

async function main() {
  const root = clerkEl();
  let clerk;
  try {
    clerk = await getPageClerk();
  } catch (e) {
    root.textContent = 'Sign-in failed to initialize. Check the extension config.';
    // eslint-disable-next-line no-console
    console.error('[lockdown] clerk init failed', e);
    return;
  }

  let mounted: 'signin' | 'done' | null = null;
  const render = () => {
    const signedIn = !!clerk.user;
    const want: 'signin' | 'done' = signedIn ? 'done' : 'signin';
    if (want === mounted) return; // no churn on repeated listener fires

    if (mounted === 'signin') clerk.unmountSignIn(root);
    root.replaceChildren();

    if (want === 'signin') {
      clerk.mountSignIn(root);
    } else {
      const box = document.createElement('div');
      box.className = 'done';
      box.innerHTML =
        '<h2>Signed in</h2><p>Monitoring is now active. You can close this tab.</p>';
      root.append(box);
    }
    mounted = want;
  };

  clerk.addListener(render);
  render();
}

main();
