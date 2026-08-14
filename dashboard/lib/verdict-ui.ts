import type { VerdictRow } from './db';

/**
 * Presentation vocabulary for verdicts. The UI deliberately has only two states
 * (design decision): "needs you" vs "logged" — severity/imminence/confidence are
 * carried by the record but never shown as a ladder.
 */

export function needsYou(v: VerdictRow): boolean {
  return v.recommended_action !== 'LOG_ONLY';
}

/** Still waiting on the parent — not yet reviewed or dismissed via the detail screen. */
export function isPending(v: VerdictRow): boolean {
  return needsYou(v) && !['reviewed', 'dismissed'].includes(v.status?.toLowerCase?.() ?? '');
}

/** Short "what we did" line for log rows. Never claims a text/email was sent —
 *  notification delivery is not wired up yet. */
export function whatWeDid(v: VerdictRow): string {
  switch (v.recommended_action) {
    case 'LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES':
      return 'Paused · resources shown';
    case 'LOCK_AND_NOTIFY':
      return 'Paused · brought to you';
    case 'LOCK':
      return 'Paused';
    default:
      return 'Logged only';
  }
}

/** The "already done" lines on the flagged card and detail screen. */
export function alreadyDone(v: VerdictRow): string[] {
  const a = v.recommended_action;
  const lines: string[] = [];
  if (a.startsWith('LOCK')) lines.push('The chat was paused on the device');
  if (a.includes('CRISIS')) lines.push('988 and Crisis Text Line were shown');
  if (a.includes('NOTIFY')) lines.push('Brought here for you to review');
  lines.push('They were told a parent would see it');
  return lines;
}

export function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

export function fmtDayHeading(d: Date): string {
  // en-GB gives "Thursday 14 August" — the handoff's heading format.
  return d.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
}

export function fmtMeta(iso: string): string {
  const d = new Date(iso);
  const day = d.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric', month: 'short' });
  return `${day}, ${fmtTime(iso)}`;
}

export function relativeTime(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 90) return 'just now';
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} hr ago`;
  const d = Math.round(h / 24);
  return d === 1 ? 'yesterday' : `${d} days ago`;
}

/** Local-date key (server timezone) for grouping rows into days. */
export function dayKey(d: Date): string {
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

export function humanCategory(v: VerdictRow): string[] {
  const chips = [v.category.replace(/_/g, ' ').toLowerCase()];
  if (v.directed_at) chips.push(`directed at ${v.directed_at.replace(/_/g, ' ').toLowerCase()}`);
  return chips;
}
