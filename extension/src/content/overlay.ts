/**
 * Lock overlay (design doc §3, §6). Rendered when a verdict crosses the lock
 * threshold; blocks further use of the chatbot on this tab. Copy is honest about
 * lifecycle: "locked pending review" (PENDING) vs "confirmed, adult notified"
 * (CONFIRMED), and never states a conclusion about the person.
 */
import { triggersNotification, type Verdict } from '../contract/verdict';

const OVERLAY_ID = 'lockdown-overlay';
let locked = false;

function copyFor(verdict: Verdict): { title: string; body: string; crisis: boolean } {
  const notified = triggersNotification(verdict.recommended_action);
  const crisis = verdict.recommended_action === 'LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES';
  if (verdict.status === 'PENDING') {
    return {
      title: 'Conversation locked — pending review',
      body: 'This conversation was flagged for review and is locked while it is checked. No conclusion has been reached.',
      crisis,
    };
  }
  return {
    title: 'Conversation locked',
    body: notified
      ? 'This conversation was flagged and a responsible adult has been notified for review. This is an observation for review, not a conclusion.'
      : 'This conversation was flagged for review. This is an observation for review, not a conclusion.',
    crisis,
  };
}

export function showLock(verdict: Verdict): void {
  if (locked) return;
  locked = true;

  const { title, body, crisis } = copyFor(verdict);
  const el = document.createElement('div');
  el.id = OVERLAY_ID;
  Object.assign(el.style, {
    position: 'fixed',
    inset: '0',
    zIndex: '2147483647',
    background: 'rgba(18,18,24,0.98)',
    color: '#f5f5f7',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '2rem',
    font: '16px/1.5 system-ui, -apple-system, sans-serif',
  } as CSSStyleDeclaration);

  const crisisHtml = crisis
    ? `<p style="margin-top:1rem;padding:0.75rem 1rem;border-radius:8px;background:#3a1d1d;">
         If there may be an immediate risk of harm, contact local emergency services (911 in the US)
         or the 988 Suicide &amp; Crisis Lifeline. This tool is not an emergency-response system.
       </p>`
    : '';

  el.innerHTML = `
    <div style="max-width:34rem">
      <h1 style="font-size:1.4rem;margin:0 0 0.5rem">${title}</h1>
      <p style="margin:0.5rem 0;color:#c7c7cc">${body}</p>
      ${crisisHtml}
      <p style="margin-top:1.25rem;font-size:0.85rem;color:#8e8e93">
        Project Lockdown — monitoring on this device is disclosed. Category:
        ${verdict.category.replace(/_/g, ' ').toLowerCase()}.
      </p>
    </div>`;

  const mount = () => {
    if (!document.getElementById(OVERLAY_ID)) document.documentElement.appendChild(el);
  };
  mount();
  document.documentElement.style.overflow = 'hidden';

  // Keep the overlay present if the SPA re-renders the DOM under it.
  new MutationObserver(mount).observe(document.documentElement, { childList: true, subtree: true });
}

export function isLocked(): boolean {
  return locked;
}
