/**
 * Client-side rolling window of recent turns (design doc §3): stateless per
 * request — less sensitive data server-side, fewer retention questions. Only the
 * window is ever sent to the core, never the full history.
 */
import type { Turn } from '../contract/verdict';

export class RollingWindow {
  private turns: Turn[] = [];

  constructor(private readonly max = 12) {}

  push(role: Turn['role'], text: string): void {
    const t = text.trim();
    if (!t) return;
    // Collapse immediate duplicates (SPAs re-fire events).
    const last = this.turns[this.turns.length - 1];
    if (last && last.role === role && last.text === t) return;
    this.turns.push({ role, text: t });
    if (this.turns.length > this.max) this.turns = this.turns.slice(-this.max);
  }

  snapshot(): Turn[] {
    return this.turns.map((t) => ({ ...t }));
  }
}
