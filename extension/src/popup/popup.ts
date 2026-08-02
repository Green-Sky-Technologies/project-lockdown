/**
 * Popup UI (vanilla). Auth is a device token the parent pastes in:
 *  - Connected  → "Monitoring active" + a Disconnect button.
 *  - Not connected → a link to generate a token in the dashboard + a paste field.
 * No Clerk, no sign-in redirect — just a stored credential.
 */
import { clearDeviceToken, getDeviceToken, setDeviceToken, settingsUrl } from '../config';

const $ = (id: string) => document.getElementById(id)!;

async function render() {
  const status = $('status');
  const actions = $('actions');
  actions.replaceChildren();

  const token = await getDeviceToken();

  if (token) {
    status.textContent = 'Monitoring active — this device is connected.';
    status.classList.add('active');

    const out = document.createElement('button');
    out.className = 'secondary';
    out.textContent = 'Disconnect this device';
    out.addEventListener('click', async () => {
      await clearDeviceToken();
      await render();
    });
    actions.append(out);
    return;
  }

  status.textContent = 'Not connected. Paste a device token to enable monitoring.';
  status.classList.remove('active');

  const getLink = document.createElement('button');
  getLink.className = 'primary';
  getLink.textContent = 'Get a device token';
  getLink.addEventListener('click', () => chrome.tabs.create({ url: settingsUrl() }));

  const input = document.createElement('input');
  input.id = 'token-input';
  input.type = 'password';
  input.placeholder = 'pld_live_…';
  input.autocomplete = 'off';

  const save = document.createElement('button');
  save.className = 'secondary';
  save.textContent = 'Connect';
  const connect = async () => {
    const value = input.value.trim();
    if (!value.startsWith('pld_live_')) {
      status.textContent = "That doesn't look like a device token (starts with pld_live_).";
      return;
    }
    await setDeviceToken(value);
    await render();
  };
  save.addEventListener('click', connect);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') void connect();
  });

  const hint = document.createElement('p');
  hint.className = 'hint';
  hint.textContent =
    'Generate a token in the dashboard, then paste it here. It stays connected until you disconnect or revoke it.';

  actions.append(getLink, input, save, hint);
}

void render();
