import { auth } from '@clerk/nextjs/server';
import { EyeSlash, MagnifyingGlass } from '@phosphor-icons/react/dist/ssr';
import { listVerdicts, type VerdictRow } from '@/lib/db';
import { fmtDayHeading, fmtTime, isPending, needsYou, whatWeDid } from '@/lib/verdict-ui';
import { PREVIEW, SAMPLE_VERDICTS } from '@/lib/sample';

export const dynamic = 'force-dynamic';

type Filter = 'all' | 'needs' | 'logged';

export default async function ActivityPage({
  searchParams,
}: {
  searchParams: Promise<{ filter?: string; q?: string }>;
}) {
  const { filter: rawFilter, q } = await searchParams;
  const filter: Filter = rawFilter === 'needs' || rawFilter === 'logged' ? rawFilter : 'all';
  const { userId, orgId } = await auth();
  if (!userId && !PREVIEW) return null; // middleware protects this route; guard for types.

  const all = (userId ? await listVerdicts(userId, orgId ?? null) : SAMPLE_VERDICTS)
    .slice()
    .sort((a, b) => +new Date(b.created_at) - +new Date(a.created_at));
  const pendingCount = all.filter(isPending).length;

  const query = (q ?? '').trim().toLowerCase();
  const rows = all.filter((v) => {
    if (filter === 'needs' && !needsYou(v)) return false;
    if (filter === 'logged' && needsYou(v)) return false;
    if (query && !v.rationale.toLowerCase().includes(query)) return false;
    return true;
  });

  // Group into days, newest first (rows arrive ordered by created_at DESC).
  const days: Array<{ heading: string; rows: VerdictRow[] }> = [];
  for (const v of rows) {
    const heading = fmtDayHeading(new Date(v.created_at));
    const last = days[days.length - 1];
    if (last?.heading === heading) last.rows.push(v);
    else days.push({ heading, rows: [v] });
  }

  const segHref = (f: Filter) =>
    `/activity${f === 'all' ? '' : `?filter=${f}`}${query ? `${f === 'all' ? '?' : '&'}q=${encodeURIComponent(query)}` : ''}`;

  return (
    <main className="content">
      <div className="asym asym-end">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h1 className="h-page">Activity</h1>
          <p className="subhead">
            {pendingCount > 0
              ? `Everything the extension has seen. ${
                  pendingCount === 1 ? 'One item is' : `${pendingCount} items are`
                } waiting for you; the rest are here only so you can look.`
              : 'Everything the extension has seen — here only so you can look.'}
          </p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
          <span className="meta" style={{ fontSize: '12.5px', color: 'color-mix(in srgb, var(--color-text) 40%, transparent)' }}>
            {all.length} on record
          </span>
          <span style={{ fontSize: '12.5px', color: 'color-mix(in srgb, var(--color-text) 40%, transparent)' }}>
            {all.filter(needsYou).length} brought to you
          </span>
        </div>
      </div>

      <div className="filters">
        <div className="seg">
          <a href={segHref('all')} aria-current={filter === 'all' ? 'true' : undefined}>
            Everything
          </a>
          <a href={segHref('needs')} aria-current={filter === 'needs' ? 'true' : undefined}>
            Needs you{pendingCount > 0 ? ` (${pendingCount})` : ''}
          </a>
          <a href={segHref('logged')} aria-current={filter === 'logged' ? 'true' : undefined}>
            Logged
          </a>
        </div>
        <form className="search" action="/activity">
          {filter !== 'all' && <input type="hidden" name="filter" value={filter} />}
          <MagnifyingGlass size={15} />
          <input
            name="q"
            defaultValue={query}
            placeholder="Search descriptions"
            aria-label="Search descriptions — searches descriptions, never message text"
          />
        </form>
      </div>

      {days.length === 0 ? (
        <p className="empty-line">
          {all.length === 0
            ? 'Nothing here yet. Once a device is connected, anything the extension takes note of lands on this page.'
            : 'Nothing matches that filter.'}
        </p>
      ) : (
        <div className="log">
          {days.map(({ heading, rows: dayRows }) => (
            <div key={heading} className="log-day">
              <span className="sectionlabel" style={{ display: 'block', paddingBottom: 10 }}>
                {heading}
              </span>
              {dayRows.map((v, i) =>
                isPending(v) ? (
                  <a key={v.id} className="logrow-hot" href={`/activity/${v.id}`}>
                    <span className="t">{fmtTime(v.created_at)}</span>
                    <span className="host">{v.chatbot_host}</span>
                    <span className="desc">
                      <span className="badge">Needs you</span>
                      <span className="txt">{v.rationale}</span>
                    </span>
                    <span className="did">{whatWeDid(v)}</span>
                    <span className="open">Open →</span>
                  </a>
                ) : (
                  <div key={v.id} className={`logrow${i === 0 ? ' first-of-day' : ''}`}>
                    <span className="t">{fmtTime(v.created_at)}</span>
                    <span className="host">{v.chatbot_host}</span>
                    <span className="desc">{v.rationale}</span>
                    <span className="did">
                      {needsYou(v) ? `${whatWeDid(v)} · ${v.status.toLowerCase()}` : whatWeDid(v)}
                    </span>
                    <a className="open" href={`/activity/${v.id}`}>
                      Open →
                    </a>
                  </div>
                ),
              )}
            </div>
          ))}
        </div>
      )}

      <div className="privacy-note">
        <EyeSlash size={18} />
        <p>
          No message text is kept anywhere — each row is a description plus the position
          of the spans that raised it. Rows fall off this log after 90 days.
        </p>
      </div>
    </main>
  );
}
