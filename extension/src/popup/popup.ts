/**
 * Popup UI (vanilla, NO Clerk UI components).
 *
 * Clerk's React-based UI (`mountSignIn` / `mountUserButton`) is unstable in an
 * MV3 popup — the popup DOM is torn down abruptly (e.g. the instant a new tab
 * opens), and React's cleanup then crashes with `removeChild`. So we mount
 * nothing from Clerk here: we read the session as DATA and render our own plain
 * DOM. Actual sign-in happens on the dashboard (the Clerk sync host, a real web
 * app); sign-out is a method call. Auth state syncs back to the extension.
 */
import { getPopupClerk } from '../auth/clerk-client';
import { SYNC_HOST } from '../config';

const $ = (id: string) => document.getElementById(id)!;

async function main() {
  const status = $('status');
  const actions = $('actions');

  let clerk;
  try {
    clerk = await getPopupClerk();
  } catch (e) {
    status.textContent = 'Sign-in unavailable — check the extension config.';
    // eslint-disable-next-line no-console
    console.error('[lockdown] clerk init failed', e);
    return;
  }

  const render = () => {
    actions.replaceChildren(); // only our own plain DOM — never a Clerk-managed node
    const user = clerk.user;
    if (user) {
      const who =
        user.primaryEmailAddress?.emailAddress ?? user.username ?? 'your account';
      status.textContent = `Monitoring active — signed in as ${who}.`;
      status.classList.add('active');

      const out = document.createElement('button');
      out.className = 'secondary';
      out.textContent = 'Sign out';
      out.addEventListener('click', () => {
        void clerk.signOut();
      });
      actions.append(out);
    } else {
      status.textContent = 'Sign in to enable monitoring.';
      status.classList.remove('active');

      const inBtn = document.createElement('button');
      inBtn.className = 'primary';
      inBtn.textContent = 'Sign in';
      inBtn.addEventListener('click', () => {
        chrome.tabs.create({ url: `${SYNC_HOST}/sign-in` });
      });

      const hint = document.createElement('p');
      hint.className = 'hint';
      hint.textContent = 'Opens sign-in in a new tab. After you sign in, reopen this popup.';

      actions.append(inBtn, hint);
    }
  };

  clerk.addListener(render); // reflect sign-in/out (incl. sync-host) without a reload
  render();
}

main();
