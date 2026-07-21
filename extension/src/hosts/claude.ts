import type { HostConfig } from './types';

export const claude: HostConfig = {
  host: 'claude.ai',
  // Claude's composer is a ProseMirror contenteditable.
  inputSelector: 'div[contenteditable="true"].ProseMirror, div[contenteditable="true"]',
  sendButtonSelector: 'button[aria-label="Send message"], button[aria-label="Send Message"]',
  // Human/assistant turns carry data-testid markers.
  turnSelector: '[data-testid="user-message"], [data-testid="assistant-message"], .font-claude-message',
  roleFor(el) {
    const testid = el.getAttribute('data-testid');
    if (testid === 'user-message') return 'user';
    if (testid === 'assistant-message') return 'assistant';
    if (el.classList.contains('font-claude-message')) return 'assistant';
    return null;
  },
};
