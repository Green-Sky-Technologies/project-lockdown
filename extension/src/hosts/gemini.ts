import type { HostConfig } from './types';

export const gemini: HostConfig = {
  host: 'gemini.google.com',
  // Gemini's composer is a rich-textarea contenteditable inside <rich-textarea>.
  inputSelector: 'rich-textarea div[contenteditable="true"], div[contenteditable="true"][role="textbox"]',
  sendButtonSelector: 'button[aria-label="Send message"], button.send-button',
  // Angular custom elements wrap each turn.
  turnSelector: 'user-query, model-response',
  roleFor(el) {
    const tag = el.tagName.toLowerCase();
    if (tag === 'user-query') return 'user';
    if (tag === 'model-response') return 'assistant';
    return null;
  },
};
