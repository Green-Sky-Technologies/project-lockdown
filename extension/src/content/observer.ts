/**
 * DOM observer (design doc §3): observes the chatbot input + rendered turns.
 * Captures the user's message on send (Enter without Shift, or the send button)
 * and scrapes assistant turns for session context. SPA-aware via event
 * delegation on the capture phase, since composers are re-created on navigation.
 */
import type { HostConfig } from '../hosts/types';
import type { RollingWindow } from './window';

type OnSend = (win: RollingWindow) => void;

function readInput(cfg: HostConfig): string {
  const el = document.querySelector(cfg.inputSelector);
  if (!el) return '';
  if (el instanceof HTMLTextAreaElement || el instanceof HTMLInputElement) return el.value;
  return (el as HTMLElement).innerText ?? '';
}

function inInput(cfg: HostConfig, target: EventTarget | null): boolean {
  return target instanceof Element && !!target.closest(cfg.inputSelector);
}

export function attachCapture(cfg: HostConfig, win: RollingWindow, onSend: OnSend): void {
  const handleSend = () => {
    const text = readInput(cfg);
    if (!text.trim()) return;
    win.push('user', text);
    onSend(win);
  };

  // Enter-to-send (Shift+Enter is a newline).
  document.addEventListener(
    'keydown',
    (e) => {
      if (e.key === 'Enter' && !e.shiftKey && inInput(cfg, e.target)) handleSend();
    },
    true,
  );

  // Explicit send button.
  if (cfg.sendButtonSelector) {
    document.addEventListener(
      'click',
      (e) => {
        const t = e.target;
        if (t instanceof Element && t.closest(cfg.sendButtonSelector!)) handleSend();
      },
      true,
    );
  }

  // Scrape assistant turns for context (user turns come from send capture).
  if (cfg.turnSelector && cfg.roleFor) {
    const seen = new WeakSet<Element>();
    const scrape = () => {
      for (const el of document.querySelectorAll(cfg.turnSelector!)) {
        if (seen.has(el)) continue;
        seen.add(el);
        const role = cfg.roleFor!(el);
        if (role === 'assistant') win.push('assistant', (el as HTMLElement).innerText ?? '');
      }
    };
    new MutationObserver(scrape).observe(document.body, { childList: true, subtree: true });
    scrape();
  }
}
