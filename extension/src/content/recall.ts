/**
 * Stage-1 recall gate (design doc §4.2): runs client-side on every send with
 * ZERO latency and ZERO cost. Its only job is RECALL — "is this plausibly worth
 * a classifier call?" Precision is the classifier's job, so the wordlist is
 * deliberately over-inclusive. A hit does NOT lock anything; it just triggers a
 * classifier call.
 */
import { WORDLIST } from '../generated/wordlist';

const TERMS = WORDLIST.map((t) => t.toLowerCase());

export function recallHit(text: string): boolean {
  const hay = text.toLowerCase();
  return TERMS.some((term) => hay.includes(term));
}
