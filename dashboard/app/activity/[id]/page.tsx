import { auth } from '@clerk/nextjs/server';
import { notFound } from 'next/navigation';
import {
  DeviceMobile,
  EyeSlash,
  Info,
  Lifebuoy,
  PauseCircle,
} from '@phosphor-icons/react/dist/ssr';
import { getVerdict } from '@/lib/db';
import { fmtMeta, humanCategory, needsYou } from '@/lib/verdict-ui';
import { PREVIEW, SAMPLE_VERDICTS } from '@/lib/sample';
import { setStatusAction } from './actions';

export const dynamic = 'force-dynamic';

// Whether to show the model's rationale/evidence. Kept behind a flag so counsel
// can decide on imminence-gated disclosure (design doc §11.2) without a code change.
const SHOW_RATIONALE = process.env.NEXT_PUBLIC_SHOW_RATIONALE !== 'false';

const HAPPENED_ICONS = [PauseCircle, Lifebuoy, DeviceMobile, Info];

export default async function ActivityDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { userId, orgId } = await auth();
  if (!userId && !PREVIEW) return null;

  // Ownership is enforced inside the query — a wrong id simply returns nothing.
  const v = userId
    ? await getVerdict(id, userId, orgId ?? null)
    : SAMPLE_VERDICTS.find((s) => s.id === id) ?? null;
  if (!v) notFound();

  const flagged = needsYou(v);
  const crisis = v.recommended_action === 'LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES';

  const happened: string[] = [];
  if (v.recommended_action.startsWith('LOCK')) happened.push('The chat was paused on the device');
  if (crisis) happened.push('988 and Crisis Text Line were shown to them');
  if (v.recommended_action.includes('NOTIFY')) happened.push('Brought here for you to review');
  happened.push('They were told a parent would see this');

  return (
    <main className="content">
      <a className="backlink" href="/activity">
        ← Activity
      </a>

      <div className="asym">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="badge-row">
            <span className={`badge${flagged ? '' : ' badge-muted'}`}>
              {flagged ? 'Needs you' : 'Logged'}
            </span>
            <span className="meta">
              {fmtMeta(v.created_at)} · {v.chatbot_host}
            </span>
          </div>
          {flagged ? (
            <>
              <h1 className="h-detail">Start with your child, not with the chat.</h1>
              <p className="lede" style={{ maxWidth: '66ch' }}>
                This is something we noticed, not a conclusion about your child. The most
                useful thing you can do tonight is be in the room.
              </p>
            </>
          ) : (
            <>
              <h1 className="h-detail">Nothing is being asked of you.</h1>
              <p className="lede" style={{ maxWidth: '66ch' }}>
                The extension noted this and moved on. It&rsquo;s here so you can look,
                not because anything needs doing.
              </p>
            </>
          )}
        </div>
        {crisis && (
          <div className="urgent-card">
            <span className="kicker kicker-accent">If it&rsquo;s urgent</span>
            <p>
              If you think your child is in danger right now, call 988 (Suicide &amp;
              Crisis Lifeline) or 911. This tool is not an emergency-response system —
              it doesn&rsquo;t call anyone for you.
            </p>
            <a href="https://988lifeline.org" style={{ fontSize: 13 }}>
              More crisis resources
            </a>
          </div>
        )}
      </div>

      <div className="rule" />

      <div className="asym">
        <div className="card-surface noticed-card">
          <span className="kicker kicker-accent">What we noticed</span>
          {SHOW_RATIONALE ? (
            <p className="body">{v.rationale}</p>
          ) : (
            <p className="body">
              A conversation on {v.chatbot_host} was brought to you for review.
            </p>
          )}
          <div className="chip-row">
            {humanCategory(v).map((c) => (
              <span key={c} className="chip">
                {c}
              </span>
            ))}
          </div>
          <div className="redaction">
            <EyeSlash size={16} />
            <p>
              Written from patterns, not quotes. We don&rsquo;t keep what was typed —
              only where in the conversation the concern appeared (
              {v.evidence_spans.length} {v.evidence_spans.length === 1 ? 'place' : 'places'}).
            </p>
          </div>
        </div>
        <div className="happened">
          <span className="kicker">What already happened</span>
          {happened.map((line, i) => {
            const Icon = HAPPENED_ICONS[Math.min(i, HAPPENED_ICONS.length - 1)];
            return (
              <div key={line} className="happened-row">
                <Icon size={16} />
                <span>{line}</span>
              </div>
            );
          })}
        </div>
      </div>

      {flagged && (
        <>
          <section style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <h2 style={{ fontSize: 15, fontWeight: 500, margin: '0 0 8px' }}>What to do next</h2>
            <div className="steps">
              <div className="step">
                <span className="step-num">1</span>
                <span className="step-title">Tonight, be nearby and unhurried</span>
                <p>
                  Sit down for something ordinary — driving, dishes, a show. Proximity
                  does more than an opener does.
                </p>
              </div>
              <div className="step">
                <span className="step-num">2</span>
                <span className="step-title">Ask directly, calmly, once</span>
                <p>
                  &ldquo;Have you been thinking about hurting yourself?&rdquo; Asking does
                  not plant the idea. Then stop talking and let the answer take as long as
                  it takes.
                </p>
              </div>
              <div className="step">
                <span className="step-num">3</span>
                <span className="step-title">Bring in one adult who isn&rsquo;t you</span>
                <p>
                  Their pediatrician, a counsellor, or the school. Same day if you can.
                  You do not have to be the whole plan.
                </p>
              </div>
            </div>
          </section>

          <div className="actionbar">
            <form action={setStatusAction.bind(null, v.id, 'reviewed')}>
              <button className="btn-accent">I&rsquo;ve talked with them</button>
            </form>
            <form action={setStatusAction.bind(null, v.id, 'snoozed')}>
              <button className="btn-neutral">Save for later</button>
            </form>
            <form action={setStatusAction.bind(null, v.id, 'dismissed')}>
              <button className="btn-ghost">This wasn&rsquo;t a concern</button>
            </form>
            <span className="reassure">Nothing you choose here is shown to your child</span>
          </div>
        </>
      )}
    </main>
  );
}
