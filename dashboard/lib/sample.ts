import type { VerdictRow } from './db';
import type { DeviceToken } from './core';

/**
 * Sample data for the design-preview mode (LOCKDOWN_PREVIEW=1, dev only): lets
 * the signed-out app render every screen with representative data so the design
 * can be reviewed without an account or a live core. Never used in production.
 */

export const PREVIEW =
  process.env.LOCKDOWN_PREVIEW === '1' && process.env.NODE_ENV !== 'production';

function daysAgo(n: number, hour: number, minute = 0): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  d.setHours(hour, minute, 0, 0);
  return d.toISOString();
}

export const SAMPLE_VERDICTS: VerdictRow[] = [
  {
    id: 'sample-1',
    verdict_id: 'v-sample-1',
    created_at: daysAgo(2, 21, 41),
    category: 'SELF_HARM',
    directed_at: 'SELF',
    severity: 'HIGH',
    confidence: 0.91,
    imminence: 'URGENT',
    stage: 'tier2',
    status: 'open',
    recommended_action: 'LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES',
    rationale:
      'Over about twenty minutes the conversation returned several times to hurting herself, and the chatbot was asked to keep it to itself. The chat was paused and 988 and Crisis Text Line were put in front of her.',
    evidence_spans: [
      { start: 120, end: 180 },
      { start: 410, end: 470 },
      { start: 890, end: 940 },
      { start: 1210, end: 1290 },
    ],
    chatbot_host: 'chat.example.com',
    capture_surface: 'extension',
    deidentified: true,
  },
  {
    id: 'sample-2',
    verdict_id: 'v-sample-2',
    created_at: daysAgo(1, 16, 12),
    category: 'VIOLENCE_OTHERS',
    directed_at: 'FICTIONAL',
    severity: 'LOW',
    confidence: 0.44,
    imminence: 'NONE',
    stage: 'tier1',
    status: 'open',
    recommended_action: 'LOG_ONLY',
    rationale: 'Violent language in a story he was writing.',
    evidence_spans: [{ start: 300, end: 360 }],
    chatbot_host: 'assistant.example.org',
    capture_surface: 'extension',
    deidentified: true,
  },
  {
    id: 'sample-3',
    verdict_id: 'v-sample-3',
    created_at: daysAgo(5, 19, 3),
    category: 'SELF_HARM',
    directed_at: 'SELF',
    severity: 'LOW',
    confidence: 0.35,
    imminence: 'NONE',
    stage: 'tier1',
    status: 'open',
    recommended_action: 'LOG_ONLY',
    rationale: 'A passing mention of feeling low, in a conversation about exams.',
    evidence_spans: [{ start: 90, end: 130 }],
    chatbot_host: 'chat.example.com',
    capture_surface: 'extension',
    deidentified: true,
  },
];

export const SAMPLE_DEVICES: DeviceToken[] = [
  {
    id: 'dev-1',
    name: "Maya's MacBook",
    created_at: daysAgo(40, 10),
    last_used_at: new Date(Date.now() - 4 * 60 * 1000).toISOString(),
    revoked: false,
  },
  {
    id: 'dev-2',
    name: "Eli's Chromebook",
    created_at: daysAgo(40, 11),
    last_used_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    revoked: false,
  },
  {
    id: 'dev-3',
    name: "Jonah's laptop",
    created_at: daysAgo(35, 9),
    last_used_at: new Date(Date.now() - 18 * 60 * 1000).toISOString(),
    revoked: false,
  },
  {
    id: 'dev-4',
    name: 'Family iPad',
    created_at: daysAgo(12, 15),
    last_used_at: null,
    revoked: false,
  },
];
