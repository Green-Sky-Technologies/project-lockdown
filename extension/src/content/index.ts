/**
 * Content-script entry. Wires the capture pipeline for the current host:
 *   observe send → rolling window → local recall gate → (hit) POST to core
 *   → verdict → lock overlay if it crosses the lock threshold.
 *
 * The recall gate keeps innocent messages entirely local; only windows that hit
 * the wordlist are sent to the core (design doc §4.2, proportionate capture §4).
 */
import { crossesLockThreshold, type ClassifyRequest, type Verdict } from '../contract/verdict';
import { hostConfigFor } from '../hosts/registry';
import type { HostConfig } from '../hosts/types';
import { attachCapture } from './observer';
import { showLock } from './overlay';
import { recallHit } from './recall';
import { RollingWindow } from './window';

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
    // Skeleton: run both tiers in one call so a single response is a confirmed
    // verdict. A production build returns the PENDING tier-1 lock immediately and
    // confirms asynchronously.
    inline_tier2: true,
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
      if (crossesLockThreshold(resp.verdict.recommended_action)) showLock(resp.verdict);
    },
  );
}
