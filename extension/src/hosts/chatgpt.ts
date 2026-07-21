import type { HostConfig } from './types';

export const chatgpt: HostConfig = {
  host: 'chatgpt.com',
  // ChatGPT's composer is a contenteditable div (#prompt-textarea); keep a
  // textarea fallback for older/alternate surfaces.
  inputSelector: '#prompt-textarea, textarea[data-testid="prompt-textarea"], div[contenteditable="true"]',
  sendButtonSelector: 'button[data-testid="send-button"]',
  turnSelector: '[data-message-author-role]',
  roleFor(el) {
    const r = el.getAttribute('data-message-author-role');
    return r === 'user' ? 'user' : r === 'assistant' ? 'assistant' : null;
  },
};
