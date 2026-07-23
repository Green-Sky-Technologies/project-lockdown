/**
 * Popup UI (vanilla, NO Clerk UI components — those crash in the ephemeral MV3
 * popup). Reads the session via the background client (data only) and renders
 * plain DOM. "Sign in" opens the extension's full-page sign-in tab (where OAuth
 * is stable); sign-out is a method call.
 */
import { getBackgroundClerk, signinPageUrl } from '../auth/clerk-client';

const $ = (id: string) => document.getElementById(id)!;

async function main() {
  const status = $('status');
  const actions = $('actions');

  let clerk;
  try {
    clerk = await getBackgroundClerk();
  } catch (e) {
    status.textContent = 'Sign-in unavailable — check the extension config.';
    // eslint-disable-next-line no-console
    console.error('[lockdown] clerk init failed', e);
    return;
  }

  const render = () => {
    actions.replaceChildren(); // only our own plain DOM
    const user = clerk.user;
    if (user) {
      const who = user.primaryEmailAddress?.emailAddress ?? user.username ?? 'your account';
      status.textContent = `Monitoring active — signed in as ${who}.`;
      status.classList.add('active');

      const out = document.createElement('button');
      out.className = 'secondary';
      out.textContent = 'Sign out';
      out.addEventListener('click', () => void clerk.signOut());
      actions.append(out);
    } else {
      status.textContent = 'Sign in to enable monitoring.';
      status.classList.remove('active');

      const inBtn = document.createElement('button');
      inBtn.className = 'primary';
      inBtn.textContent = 'Sign in';
      inBtn.addEventListener('click', () => {
        chrome.tabs.create({ url: signinPageUrl() });
      });

      const hint = document.createElement('p');
      hint.className = 'hint';
      hint.textContent = 'Opens a sign-in page. After you sign in, reopen this popup.';

      actions.append(inBtn, hint);
    }
  };

  clerk.addListener(render);
  render();
}

main();
