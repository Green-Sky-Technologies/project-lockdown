import { auth } from '@clerk/nextjs/server';
import { notFound } from 'next/navigation';
import { getVerdict } from '@/lib/db';

export const dynamic = 'force-dynamic';

// Whether to show the model's rationale/evidence. Kept behind a flag so counsel
// can decide on imminence-gated disclosure (design doc §11.2) without a code change.
const SHOW_RATIONALE = process.env.NEXT_PUBLIC_SHOW_RATIONALE !== 'false';

export default async function VerdictDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { userId, orgId } = await auth();
  if (!userId) return null;

  // Ownership is enforced inside the query — a wrong id simply returns nothing.
  const v = await getVerdict(id, userId, orgId ?? null);
  if (!v) notFound();

  return (
    <section className="detail">
      <a className="navlink" href="/verdicts">
        ← Back
      </a>
      <h1>Flagged conversation</h1>
      <p className="muted">
        An observation flagged for your review — not a conclusion about a person.
      </p>

      <dl className="fields">
        <dt>Category</dt>
        <dd>{v.category.replace(/_/g, ' ').toLowerCase()}</dd>
        <dt>Directed at</dt>
        <dd>{v.directed_at.toLowerCase()}</dd>
        <dt>Severity</dt>
        <dd>{v.severity}</dd>
        <dt>Imminence</dt>
        <dd>{v.imminence}</dd>
        <dt>Confidence</dt>
        <dd>{(v.confidence * 100).toFixed(0)}%</dd>
        <dt>Outcome</dt>
        <dd>{v.recommended_action}</dd>
        <dt>Stage / status</dt>
        <dd>
          {v.stage} · {v.status}
        </dd>
        <dt>Where</dt>
        <dd>
          {v.chatbot_host} ({v.capture_surface})
        </dd>
        <dt>When</dt>
        <dd>{new Date(v.created_at).toLocaleString()}</dd>
      </dl>

      {SHOW_RATIONALE && (
        <>
          <h2>Why it was flagged</h2>
          <p>{v.rationale}</p>
          <p className="muted small">
            No message text is stored — only the offsets of the spans that triggered
            the flag ({v.evidence_spans.length}).
          </p>
        </>
      )}

      {v.recommended_action === 'LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES' && (
        <p className="crisis">
          If you believe there may be an immediate risk of harm, contact local
          emergency services (911 in the US) or the 988 Suicide &amp; Crisis
          Lifeline. This tool is not an emergency-response system.
        </p>
      )}
    </section>
  );
}
