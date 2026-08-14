import { auth, currentUser } from '@clerk/nextjs/server';
import { PREVIEW } from '@/lib/sample';

export const dynamic = 'force-dynamic';

/**
 * Household, notification route, data policy. Two of the three sections are ahead
 * of the backend by design: there is no children model yet, and text/email alerts
 * aren't wired up — those affordances render disabled and say so, rather than
 * pretending to work.
 */
export default async function SettingsPage() {
  const { userId } = await auth();
  if (!userId && !PREVIEW) return null; // middleware protects this route; guard for types.

  const user = userId ? await currentUser() : null;
  const email = user?.primaryEmailAddress?.emailAddress;

  return (
    <main className="content">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h1 className="h-page">Settings</h1>
        <p className="subhead">
          Who&rsquo;s in the household, how you hear about something, and what this keeps.
        </p>
      </div>

      <div className="setrow">
        <div className="setlabel">
          <span className="lbl">Kids</span>
          <span className="cap">Names are only ever visible to you.</span>
        </div>
        <div className="setbody">
          <p className="kept-prose">
            No kids added yet. Naming your kids will let activity say who a conversation
            belonged to instead of just which device it happened on.
          </p>
          <button className="btn-neutral btn-sm" style={{ alignSelf: 'flex-start' }} disabled>
            Add a child — coming soon
          </button>
        </div>
      </div>

      <div className="setrow">
        <div className="setlabel">
          <span className="lbl">How we reach you</span>
          <span className="cap">Only ever when something needs you.</span>
        </div>
        <div className="setbody">
          <div className="radio-row is-disabled">
            <span className="radio-dot" />
            <div className="rlabel">
              <span className="rl">Text me straight away</span>
              <span className="rc">Coming soon</span>
            </div>
          </div>
          <div className="radio-row is-disabled">
            <span className="radio-dot" />
            <div className="rlabel">
              <span className="rl">Email me instead</span>
              <span className="rc">{email ? `${email} · coming soon` : 'Coming soon'}</span>
            </div>
          </div>
          <div className="radio-row">
            <span className="radio-dot is-checked" />
            <div className="rlabel">
              <span className="rl">Only in the dashboard</span>
              <span className="rc">
                For now, anything that needs you appears here first — nothing arrives on
                your phone yet.
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="setrow">
        <div className="setlabel">
          <span className="lbl">What&rsquo;s kept</span>
          <span className="cap">Fixed by design, not a preference.</span>
        </div>
        <div className="setbody">
          <p className="kept-prose">
            No message text is stored — only a written description of what was noticed
            and the position of the spans that raised it. Activity is deleted after 90
            days. Your kids are told the extension is running and told when something has
            been sent to you.
          </p>
          <div className="kept-links">
            <a href="/privacy">Privacy policy</a>
            <a href="mailto:support@greensky.tech?subject=Data%20export%20request">
              Download everything we hold
            </a>
            <a
              className="quiet"
              href="mailto:support@greensky.tech?subject=Account%20deletion%20request"
            >
              Delete this account
            </a>
          </div>
        </div>
      </div>
    </main>
  );
}
