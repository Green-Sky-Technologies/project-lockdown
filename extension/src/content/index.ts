/**
 * Content-script entry. Wires the capture pipeline for the current host:
 *   observe send → rolling window → local recall gate → (hit) POST to core
 *   → verdict → lock overlay if it crosses the lock threshold.
 *
 * The recall gate keeps innocent messages entirely local; only windows that hit
 * the wordlist are sent to the core (design doc §4.2, proportionate capture §4).
 */
import {
  crossesLockThreshold,
  type ClassifyRequest,
  type Verdict,
  type VerdictStatus,
} from '../contract/verdict';
import { hostConfigFor } from '../hosts/registry';
import type { HostConfig } from '../hosts/types';
import { attachCapture } from './observer';
import { releaseLock, showLock, updateLock } from './overlay';
import { recallHit } from './recall';
import { RollingWindow } from './window';

// Post-lock polling cadence: the tier-2 verdict usually lands in ~3s; give up
// after ~30s and keep the (recoverable §2) lock for parent review.
const POLL_INTERVAL_MS = 2000;
const POLL_MAX_ATTEMPTS = 15;

const cfg = resolveConfig();
if (cfg) init(cfg);

/**
 * Resolve the host adapter. Real sites match directly on location.host — that
 * path is unchanged. The mock test site (a single Vercel domain that emulates
 * each host) advertises which host it is imitating via a data attribute; we only
 * consult it when no real host matched, so production behavior is untouched.
 */
function resolveConfig(): HostConfig | null {
  const direct = hostConfigFor(location.host);
  if (direct) return direct;
  const emulate = document.documentElement.dataset.lockdownEmulate;
  return emulate ? hostConfigFor(emulate) : null;
}

function init(cfg: HostConfig): void {
  const win = new RollingWindow();
  attachCapture(cfg, win, (w) => maybeClassify(cfg, w));
  // eslint-disable-next-line no-console
  console.debug('[lockdown] active as', cfg.host, 'on', location.host);
}

function maybeClassify(cfg: HostConfig, win: RollingWindow): void {
  const turns = win.snapshot();
  const joined = turns.map((t) => t.text).join('\n');
  if (!recallHit(joined)) return; // stays local — no classifier call

  const payload: ClassifyRequest = {
    windowed_text: turns,
    category_set: ['VIOLENCE_TO_OTHERS'],
    client_metadata: {
      chatbot_host: cfg.host,
      capture_surface: 'CHROMIUM_EXT',
      monitored_categories: ['VIOLENCE_TO_OTHERS'],
    },
    // Async mode: the core answers with the PENDING tier-1 verdict (the lock
    // lands at tier-1 latency) and verifies with tier-2 in the background; we
    // poll /verdict-status to unlock on OVERTURNED or harden on CONFIRMED.
    inline_tier2: false,
  };

  chrome.runtime.sendMessage(
    { type: 'classify', payload },
    (resp?: { ok: boolean; verdict?: Verdict; error?: string; needsSetup?: boolean }) => {
      if (chrome.runtime.lastError || !resp) return;
      if (resp.needsSetup) {
        // eslint-disable-next-line no-console
        console.warn(
          '[lockdown] connect a device token via the Project Lockdown popup to enable monitoring.',
        );
        return;
      }
      if (!resp.ok || !resp.verdict) return;
      const verdict = resp.verdict;
      if (!crossesLockThreshold(verdict.recommended_action)) return;
      showLock(verdict);
      if (verdict.status === 'PENDING') pollVerdict(verdict);
    },
  );
}

/** Poll the tier-2 outcome for a PENDING lock: OVERTURNED lifts the overlay,
 * CONFIRMED updates its copy ("adult notified"). Polling stops after a bounded
 * number of attempts — an unresolved verdict keeps the recoverable lock. */
function pollVerdict(pending: Verdict, attempt = 0): void {
  if (attempt >= POLL_MAX_ATTEMPTS) return;
  setTimeout(() => {
    chrome.runtime.sendMessage(
      { type: 'verdictStatus', verdictId: pending.verdict_id },
      (resp?: { ok: boolean; status?: VerdictStatus; error?: string }) => {
        if (chrome.runtime.lastError) return;
        const s = resp?.status;
        // 404 until the background tier-2 row lands — keep polling.
        if (!resp?.ok || !s || s.stage === 'TIER1') {
          pollVerdict(pending, attempt + 1);
          return;
        }
        if (s.status === 'OVERTURNED') {
          releaseLock();
          return;
        }
        updateLock({ ...pending, status: s.status, recommended_action: s.recommended_action });
      },
    );
  }, POLL_INTERVAL_MS);
}
