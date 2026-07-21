/**
 * Mock chatbot harness for testing the Project Lockdown extension.
 *
 * There is NO model here. Its only job is to reproduce, per host, the EXACT DOM
 * hooks each extension adapter listens for (extension/src/hosts/*.ts), so the
 * real content script captures input, the real recall gate fires, the real core
 * classifies, and the real lock overlay renders. On send it appends a user turn
 * and, a beat later, a canned assistant turn.
 *
 * Hosts are data (mirrors the extension's "hosts are data" design): each entry
 * builds the composer + send button and manufactures user/assistant turn nodes
 * with the selectors/attributes that host's adapter keys off. Switching host
 * reloads the page with ?host=… so the content script re-inits cleanly.
 */

const HOSTS = {
  // --- chatgpt.com — adapter: extension/src/hosts/chatgpt.ts ---------------
  'chatgpt.com': {
    label: 'ChatGPT',
    theme: 'chatgpt',
    placeholder: 'Message ChatGPT',
    assistantName: 'ChatGPT',
    // input #prompt-textarea (contenteditable); send button[data-testid="send-button"]
    buildComposer() {
      const input = el('div', { id: 'prompt-textarea', contenteditable: 'true', 'data-placeholder': this.placeholder, role: 'textbox' });
      const send = el('button', { 'data-testid': 'send-button', 'aria-label': 'Send prompt', type: 'button' }, '↑');
      return { input, send };
    },
    // turns carry data-message-author-role="user"|"assistant"
    userTurn(text) {
      return el('div', { 'data-message-author-role': 'user', class: 'msg user' }, bubble(text));
    },
    assistantTurn(text) {
      return el('div', { 'data-message-author-role': 'assistant', class: 'msg assistant' }, bubble(text));
    },
  },

  // --- claude.ai — adapter: extension/src/hosts/claude.ts ------------------
  'claude.ai': {
    label: 'Claude',
    theme: 'claude',
    placeholder: 'How can I help you today?',
    assistantName: 'Claude',
    // input div.ProseMirror[contenteditable]; send button[aria-label="Send message"]
    buildComposer() {
      const input = el('div', { class: 'ProseMirror', contenteditable: 'true', 'data-placeholder': this.placeholder, role: 'textbox' });
      const send = el('button', { 'aria-label': 'Send message', type: 'button' }, '↑');
      return { input, send };
    },
    // user: [data-testid="user-message"]; assistant: [data-testid="assistant-message"].font-claude-message
    userTurn(text) {
      return el('div', { 'data-testid': 'user-message', class: 'msg user' }, bubble(text));
    },
    assistantTurn(text) {
      return el('div', { 'data-testid': 'assistant-message', class: 'msg assistant font-claude-message' }, bubble(text));
    },
  },

  // --- gemini.google.com — adapter: extension/src/hosts/gemini.ts ----------
  'gemini.google.com': {
    label: 'Gemini',
    theme: 'gemini',
    placeholder: 'Ask Gemini',
    assistantName: 'Gemini',
    // input rich-textarea div[contenteditable][role="textbox"]; send button[aria-label="Send message"]
    buildComposer() {
      const inner = el('div', { contenteditable: 'true', role: 'textbox', 'data-placeholder': this.placeholder });
      const input = el('rich-textarea', {}, inner);
      const send = el('button', { 'aria-label': 'Send message', class: 'send-button', type: 'button' }, '➤');
      // The extension reads the contenteditable; expose it for send/clear.
      input._editable = inner;
      return { input, send };
    },
    // turns are custom elements <user-query> / <model-response>
    userTurn(text) {
      return el('user-query', { class: 'msg user' }, bubble(text));
    },
    assistantTurn(text) {
      return el('model-response', { class: 'msg assistant' }, bubble(text));
    },
  },
};

const CANNED_REPLIES = [
  "I can't help with anything that could put people at risk, but I'm happy to help with something else.",
  "Thanks for the message! This is a mock response — there's no real model here.",
  "Got it. (Canned reply from the Project Lockdown test harness.)",
  "Understood — let me know what else you'd like to try.",
];

// --- tiny DOM helpers -------------------------------------------------------
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const c of children) node.append(c instanceof Node ? c : document.createTextNode(c));
  return node;
}
function bubble(text) {
  return el('div', { class: 'bubble' }, text);
}

// --- host resolution --------------------------------------------------------
function currentHostKey() {
  const q = new URLSearchParams(location.search).get('host');
  return HOSTS[q] ? q : 'chatgpt.com';
}

// --- app wiring -------------------------------------------------------------
let replyIndex = 0;

function readComposer(input) {
  const editable = input._editable ?? input;
  return (editable.innerText || '').trim();
}
function clearComposer(input) {
  const editable = input._editable ?? input;
  editable.innerText = '';
}

function boot() {
  const hostKey = currentHostKey();
  const host = HOSTS[hostKey];

  // Advertise which host we emulate BEFORE the extension's document_idle inject.
  document.documentElement.dataset.lockdownEmulate = hostKey;
  document.documentElement.dataset.theme = host.theme;

  buildSwitcher(hostKey);

  const thread = document.getElementById('thread');
  const composerMount = document.getElementById('composer-input');
  const sendMount = document.getElementById('composer-send');

  const { input, send } = host.buildComposer();
  composerMount.replaceChildren(input);
  sendMount.replaceChildren(send);
  document.getElementById('brand').textContent = host.label;

  function submit() {
    const text = readComposer(input);
    if (!text) return;
    thread.append(host.userTurn(text));
    clearComposer(input);
    scrollThread(thread);
    // Canned assistant reply a beat later (no model).
    setTimeout(() => {
      const reply = CANNED_REPLIES[replyIndex++ % CANNED_REPLIES.length];
      thread.append(host.assistantTurn(reply));
      scrollThread(thread);
    }, 600);
  }

  // The mock handles its OWN submit for UX. The extension listens independently
  // on the same Enter/click via document-level capture — both fire.
  const editable = input._editable ?? input;
  editable.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  });
  send.addEventListener('click', submit);
  editable.focus();
}

function scrollThread(thread) {
  thread.scrollTop = thread.scrollHeight;
}

function buildSwitcher(activeKey) {
  const bar = document.getElementById('switcher');
  bar.replaceChildren(
    ...Object.entries(HOSTS).map(([key, h]) => {
      const b = el('button', { class: 'switch' + (key === activeKey ? ' active' : ''), type: 'button' }, h.label);
      b.addEventListener('click', () => {
        const url = new URL(location.href);
        url.searchParams.set('host', key);
        location.href = url.toString(); // reload so the content script re-inits
      });
      return b;
    }),
  );
}

document.addEventListener('DOMContentLoaded', boot);
