/**
 * TypeScript view of the verdict contract.
 *
 * MIRRORS `contract/verdict.schema.json` and `contract/classify-request.schema.json`
 * (the single sources of truth). Keep in sync — regenerate/verify via
 * `contract/codegen/gen_ts.mjs`. Do not add fields here without adding them to
 * the schema first (design doc §5).
 */

export const SCHEMA_VERSION = '1.0.0' as const;

export type Stage = 'RECALL_GATE' | 'TIER1' | 'TIER2' | 'HUMAN';
export type Status = 'PENDING' | 'CONFIRMED' | 'CLEARED' | 'OVERTURNED';
export type Category = 'VIOLENCE_TO_OTHERS';
export type DirectedAt = 'OTHERS' | 'SELF' | 'FICTIONAL_OR_ACADEMIC' | 'AMBIGUOUS';
export type Severity = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
export type Imminence = 'NONE' | 'SPECULATIVE' | 'DEVELOPING' | 'IMMINENT';
export type RecommendedAction =
  | 'NO_ACTION'
  | 'LOG_ONLY'
  | 'LOCK'
  | 'LOCK_AND_NOTIFY'
  | 'LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES';
export type CaptureSurface =
  | 'CHROMIUM_EXT'
  | 'FIREFOX_EXT'
  | 'MANAGED_CHROMEOS'
  | 'NATIVE_AGENT'
  | 'NETWORK_PROXY';
export type ReviewerOutcome = 'CONFIRM' | 'OVERTURN' | 'NEEDS_MORE';

export interface EvidenceSpan {
  start: number;
  end: number;
  turn_index?: number | null;
}

export interface Context {
  window_turn_count: number;
  chatbot_host: string;
  capture_surface: CaptureSurface;
  monitored_categories: Category[];
}

export interface Review {
  reviewed_by: string | null;
  reviewed_at: string | null;
  reviewer_outcome: ReviewerOutcome | null;
  notes: string | null;
}

export interface Sampling {
  is_holdout: boolean;
  suppression_eligible: boolean;
}

export interface Privacy {
  deidentified: boolean;
  retain_as_training: boolean;
  raw_text_ref: string | null;
}

export interface Verdict {
  schema_version: string;
  verdict_id: string;
  created_at: string;
  stage: Stage;
  status: Status;
  category: Category;
  directed_at: DirectedAt;
  severity: Severity;
  confidence: number;
  imminence: Imminence;
  recommended_action: RecommendedAction;
  rationale: string;
  evidence_spans: EvidenceSpan[];
  context: Context;
  review?: Review | null;
  sampling: Sampling;
  privacy: Privacy;
}

// --- request contract ------------------------------------------------------
export interface Turn {
  role: 'user' | 'assistant';
  text: string;
}

export interface ClientMetadata {
  chatbot_host: string;
  capture_surface: CaptureSurface;
  monitored_categories: Category[];
}

export interface ClassifyRequest {
  windowed_text: Turn[];
  category_set: Category[];
  client_metadata: ClientMetadata;
  inline_tier2?: boolean;
}

// --- shared decision helpers (mirror core/contract/actions.py) -------------

/** Actions at/above which the extension renders the lock overlay. */
export function crossesLockThreshold(action: RecommendedAction): boolean {
  return action !== 'NO_ACTION' && action !== 'LOG_ONLY';
}

/** True once an adult has been (or will be) notified — drives overlay copy. */
export function triggersNotification(action: RecommendedAction): boolean {
  return (
    action === 'LOCK_AND_NOTIFY' ||
    action === 'LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES'
  );
}
