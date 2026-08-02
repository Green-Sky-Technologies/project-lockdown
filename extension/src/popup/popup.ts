/**
 * Popup UI (vanilla). In DEV bypass builds (DEV_SKIP_AUTH=1) it shows a dev
 * banner and never touches Clerk. Otherwise it reads the session via the
 * background client (data only, no Clerk UI — those crash in the MV3 popup) and
 * offers Sign in (opens the full-page sign-in tab) / Sign out.
 */
const $ = (id: string) => document.getElementById(id)!;

declare const __DEV_SKIP_AUTH__: boolean;

async function main() {
  const status = $('status');
  const actions = $('actions');

  if (__DEV_SKIP_AUTH__) {
    status.textContent = 'Dev mode — auth bypassed. Monitoring is active without sign-in.';
    status.classList.add('active');
    return;
  }

  // Clerk is imported dynamically so a dev build doesn't bundle it into popup.js.
  const { getBackgroundClerk } = await import('../auth/clerk-client');
  const { signinUrl } = await import('../config');

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
    actions.replaceChildren();
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
      inBtn.addEventListener('click', () => chrome.tabs.create({ url: signinUrl() }));

      const hint = document.createElement('p');
      hint.className = 'hint';
      hint.textContent =
        'Opens the dashboard to sign in. After you sign in there, reopen this popup.';

      actions.append(inBtn, hint);
    }
  };

  clerk.addListener(render);
  render();
}

main();
