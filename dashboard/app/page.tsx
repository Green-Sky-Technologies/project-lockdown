import { auth } from '@clerk/nextjs/server';
import { SignInButton } from '@clerk/nextjs';
import { EyeSlash, ShieldCheck } from '@phosphor-icons/react/dist/ssr';
import { listVerdicts, type VerdictRow } from '@/lib/db';
import { listDeviceTokens, type DeviceToken } from '@/lib/core';
import { PREVIEW, SAMPLE_DEVICES, SAMPLE_VERDICTS } from '@/lib/sample';
import {
  alreadyDone,
  dayKey,
  fmtTime,
  humanCategory,
  isPending,
  needsYou,
  relativeTime,
} from '@/lib/verdict-ui';

// Live per-request data scoped to the signed-in parent — never prerender.
export const dynamic = 'force-dynamic';

function SignedOutHero() {
  return (
    <main className="content content-home">
      <div className="hero-out">
        <h1 className="h-hero">When something needs a parent, it says so plainly.</h1>
        <p className="lede">
          This dashboard shows conversations that Project Lockdown flagged for your
          review. Monitoring is disclosed to the person being monitored. What you see
          here is an observation for review — never a conclusion about a person.
        </p>
        <SignInButton mode="modal">
          <button className="btn-accent">Sign in to continue</button>
        </SignInButton>
      </div>
    </main>
  );
}

export default async function Home() {
  const { userId, orgId } = await auth();
  if (!userId && !PREVIEW) return <SignedOutHero />;

  const verdicts = userId ? await listVerdicts(userId, orgId ?? null) : SAMPLE_VERDICTS;
  let devices: DeviceToken[] = userId ? [] : SAMPLE_DEVICES;
  if (userId) {
    try {
      devices = (await listDeviceTokens()).filter((t) => !t.revoked);
    } catch {
      // The device rail degrades to empty if the core is unreachable; the page still renders.
    }
  }

  const connected = devices.filter((d) => d.last_used_at);

  // The last 7 days, newest first, each with its verdicts (server-local dates).
  const byDay = new Map<string, VerdictRow[]>();
  for (const v of verdicts) {
    const k = dayKey(new Date(v.created_at));
    byDay.set(k, [...(byDay.get(k) ?? []), v]);
  }
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - i);
    return { date: d, rows: byDay.get(dayKey(d)) ?? [] };
  });

  const weekRows = days.flatMap((d) => d.rows);
  const broughtToYou = weekRows.filter(needsYou).length;
  const pendingToday = days[0].rows.filter(isPending).length;

  return (
    <main className="content content-home">
      <div className="asym">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, alignItems: 'flex-start' }}>
          <span className="pill">
            <ShieldCheck size={14} />
            {connected.length > 0
              ? `Watching · ${connected.length} device${connected.length === 1 ? '' : 's'}`
              : 'No devices connected yet'}
          </span>
          <h1 className="h-hero">
            {pendingToday > 0
              ? pendingToday === 1
                ? 'One conversation needs you today.'
                : `${pendingToday} conversations need you today.`
              : "Everything's ordinary today."}
          </h1>
          <p className="lede">
            You don&rsquo;t have to read this page every day. It stays this quiet unless
            there&rsquo;s something a parent should know, and then it&rsquo;s the first
            thing you&rsquo;ll see here.
          </p>
        </div>
        <div className="device-list">
          <span className="kicker">Devices</span>
          {devices.length === 0 ? (
            <span className="device-line is-off">
              <span className="dot-off" />
              Nothing connected
              <a className="when" href="/devices" style={{ marginLeft: 'auto' }}>
                Connect
              </a>
            </span>
          ) : (
            devices.map((d) => (
              <span key={d.id} className={`device-line${d.last_used_at ? '' : ' is-off'}`}>
                <span className={d.last_used_at ? 'dot-on' : 'dot-off'} />
                {d.name || 'Unnamed device'}
                <span className="when">
                  {d.last_used_at ? relativeTime(d.last_used_at) : 'not connected'}
                </span>
              </span>
            ))
          )}
          <a href="/devices" style={{ fontSize: '12.5px', marginTop: 2 }}>
            Manage devices
          </a>
        </div>
      </div>

      <div className="rule" />

      <section style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div className="week-head">
          <span className="sectionlabel">This week</span>
          <span className="meta-count">
            {broughtToYou === 0
              ? 'Nothing brought to you'
              : `${broughtToYou} brought to you`}
          </span>
          <a href="/activity">Open the full log</a>
        </div>

        {days.map(({ date, rows }, i) => {
          const flagged = rows.filter(isPending);
          const quiet = rows.filter((v) => !isPending(v));
          return (
            <div key={dayKey(date)} className={`dayrow${i > 2 ? ' is-past' : ''}`}>
              <div className="daycell">
                <span className="dow">
                  {date.toLocaleDateString('en-US', { weekday: 'short' })}
                </span>
                <span className="date">
                  {date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' })}
                </span>
              </div>
              <div className="daybody">
                {flagged.map((v) => (
                  <a key={v.id} className="flagged-card" href={`/activity/${v.id}`}>
                    <div className="flagged-main">
                      <div className="badge-row">
                        <span className="badge">Needs you</span>
                        <span className="meta">
                          {fmtTime(v.created_at)} · {v.chatbot_host}
                        </span>
                      </div>
                      <span className="flagged-title">One conversation needs you</span>
                      <p className="flagged-desc">{v.rationale}</p>
                      <span className="flagged-cta">Read what to do next →</span>
                    </div>
                    <div className="flagged-aside">
                      <span className="kicker">Already done</span>
                      {alreadyDone(v).map((line) => (
                        <span key={line}>{line}</span>
                      ))}
                    </div>
                  </a>
                ))}
                {flagged.length > 0 ? (
                  <span className="day-aftermath">
                    Everything else that day looked ordinary.
                  </span>
                ) : (
                  <span className="quiet-summary">Nothing of concern.</span>
                )}
                {quiet.length > 0 && (
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {quiet.map((v) => (
                      <a
                        key={v.id}
                        href={`/activity/${v.id}`}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 7,
                          fontSize: '12.5px',
                          padding: '5px 11px',
                          borderRadius: 6,
                          background: 'color-mix(in srgb, var(--color-text) 4%, transparent)',
                          color: 'color-mix(in srgb, var(--color-text) 60%, transparent)',
                        }}
                      >
                        {humanCategory(v)[0]} · {needsYou(v) ? 'handled' : 'logged only'}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        <div className="dayrow">
          <a href="/activity" style={{ fontSize: '13.5px', color: 'color-mix(in srgb, var(--color-text) 50%, transparent)' }}>
            Earlier ↓
          </a>
        </div>
      </section>

      <div className="privacy-note">
        <EyeSlash size={18} />
        <p>
          We never keep what your kids type. They can see that this is running, and the
          extension tells them plainly when a conversation has been sent to you. What you
          read here is a description, not a transcript.
        </p>
      </div>
    </main>
  );
}
