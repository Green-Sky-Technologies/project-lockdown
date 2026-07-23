import { neon } from '@neondatabase/serverless';

/**
 * Neon HTTP driver reads, always scoped to the signed-in account. Callers pass
 * the `userId`/`orgId` from Clerk's server-side `auth()` — never a client-supplied
 * id — so there is no cross-account leakage. Queries are parameterized (tagged
 * template), so values are never interpolated into SQL.
 *
 * The store holds NO raw text (the verdict contract carries none) — only the
 * render fields + offset evidence spans.
 */

export interface VerdictRow {
  id: string;
  verdict_id: string;
  created_at: string;
  category: string;
  directed_at: string;
  severity: string;
  confidence: number;
  imminence: string;
  stage: string;
  status: string;
  recommended_action: string;
  rationale: string;
  evidence_spans: Array<{ start: number; end: number; turn_index?: number | null }>;
  chatbot_host: string;
  capture_surface: string;
  deidentified: boolean;
}

function sql() {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error('DATABASE_URL is not set');
  return neon(url);
}

/** List this account's flagged verdicts (own rows, plus org rows for school-tier). */
export async function listVerdicts(userId: string, orgId: string | null): Promise<VerdictRow[]> {
  const db = sql();
  const rows = orgId
    ? await db`
        SELECT vr.* FROM verdict_records vr
        JOIN accounts a ON a.id = vr.account_id
        WHERE a.clerk_user_id = ${userId} OR vr.clerk_org_id = ${orgId}
        ORDER BY vr.created_at DESC LIMIT 200`
    : await db`
        SELECT vr.* FROM verdict_records vr
        JOIN accounts a ON a.id = vr.account_id
        WHERE a.clerk_user_id = ${userId}
        ORDER BY vr.created_at DESC LIMIT 200`;
  return rows as VerdictRow[];
}

/** Fetch one verdict, enforcing ownership in the query (never trust the URL id). */
export async function getVerdict(
  id: string,
  userId: string,
  orgId: string | null,
): Promise<VerdictRow | null> {
  const db = sql();
  const rows = orgId
    ? await db`
        SELECT vr.* FROM verdict_records vr
        JOIN accounts a ON a.id = vr.account_id
        WHERE vr.id = ${id} AND (a.clerk_user_id = ${userId} OR vr.clerk_org_id = ${orgId})
        LIMIT 1`
    : await db`
        SELECT vr.* FROM verdict_records vr
        JOIN accounts a ON a.id = vr.account_id
        WHERE vr.id = ${id} AND a.clerk_user_id = ${userId}
        LIMIT 1`;
  return (rows[0] as VerdictRow) ?? null;
}
