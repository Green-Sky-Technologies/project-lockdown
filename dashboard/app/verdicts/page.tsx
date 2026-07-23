import { auth } from '@clerk/nextjs/server';
import { listVerdicts, type VerdictRow } from '@/lib/db';

// Reads live per-request data scoped to the signed-in user — never prerender.
export const dynamic = 'force-dynamic';

function actionLabel(a: string): string {
  return a
    .replace('LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES', 'Locked · notified · crisis resources')
    .replace('LOCK_AND_NOTIFY', 'Locked · adult notified')
    .replace('LOG_ONLY', 'Logged')
    .replace('LOCK', 'Locked · pending review');
}

export default async function VerdictsPage() {
  const { userId, orgId } = await auth();
  if (!userId) return null; // middleware protects this route; guard for types.

  const rows: VerdictRow[] = await listVerdicts(userId, orgId ?? null);

  return (
    <section>
      <h1>Flagged conversations</h1>
      <p className="muted">
        Observations flagged for your review — not conclusions. {rows.length} shown.
      </p>

      {rows.length === 0 ? (
        <p className="empty">Nothing flagged yet.</p>
      ) : (
        <table className="verdicts">
          <thead>
            <tr>
              <th>When</th>
              <th>Where</th>
              <th>Severity</th>
              <th>Imminence</th>
              <th>Outcome</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((v) => (
              <tr key={v.id}>
                <td>{new Date(v.created_at).toLocaleString()}</td>
                <td>{v.chatbot_host}</td>
                <td>{v.severity}</td>
                <td>{v.imminence}</td>
                <td>{actionLabel(v.recommended_action)}</td>
                <td>{v.status}</td>
                <td>
                  <a className="navlink" href={`/verdicts/${v.id}`}>
                    Details →
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
