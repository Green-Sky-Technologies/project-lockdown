import { auth } from '@clerk/nextjs/server';
import { Laptop, Plus } from '@phosphor-icons/react/dist/ssr';
import { listDeviceTokens, type DeviceToken } from '@/lib/core';
import { relativeTime } from '@/lib/verdict-ui';
import { PREVIEW, SAMPLE_DEVICES } from '@/lib/sample';
import { ConnectDevice } from './ConnectDevice';
import { revokeTokenAction } from './actions';

export const dynamic = 'force-dynamic';

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
}

export default async function DevicesPage() {
  const { userId } = await auth();
  if (!userId && !PREVIEW) return null; // middleware protects this route; guard for types.

  let tokens: DeviceToken[] = userId ? [] : SAMPLE_DEVICES;
  let error: string | null = null;
  if (userId) {
    try {
      tokens = (await listDeviceTokens()).filter((t) => !t.revoked);
    } catch {
      error = 'Could not reach the detection service. Try again in a moment.';
    }
  }

  return (
    <main className="content" style={{ gap: 30 }}>
      <div className="asym asym-end">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h1 className="h-page">Devices</h1>
          <p className="subhead">
            One token per browser. Nothing is watched until the extension is connected,
            and the child is told when it is.
          </p>
        </div>
        <a className="btn-accent devices-connect" href="#connect">
          <Plus size={15} />
          Connect a device
        </a>
      </div>

      {error ? (
        <p className="empty-line">{error}</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="devgrid devhead">
            <span>Device</span>
            <span>Last seen</span>
            <span>State</span>
            <span />
          </div>
          {tokens.length === 0 ? (
            <p className="empty-line" style={{ borderTop: '1px solid color-mix(in srgb, var(--color-text) 12%, transparent)' }}>
              Nothing connected yet. Create a token below to connect the first device.
            </p>
          ) : (
            tokens.map((t) => {
              const connected = Boolean(t.last_used_at);
              return (
                <div key={t.id} className="devgrid devrow">
                  <div className={`dev-id${connected ? '' : ' is-off'}`}>
                    <Laptop size={19} />
                    <div className="dev-name">
                      <span className="nm">{t.name || 'Unnamed device'}</span>
                      <span className="sub">
                        {connected
                          ? `Connected ${fmtDate(t.created_at)}`
                          : `Token created ${fmtDate(t.created_at)}, never used`}
                      </span>
                    </div>
                  </div>
                  <span className="dev-seen">
                    {t.last_used_at ? relativeTime(t.last_used_at) : '—'}
                  </span>
                  <span className={`dev-state${connected ? '' : ' is-off'}`}>
                    <span className="dot" />
                    {connected ? 'Watching' : 'Not connected'}
                  </span>
                  <div className="dev-actions">
                    <form action={revokeTokenAction.bind(null, t.id)}>
                      <button>{connected ? 'Disconnect' : 'Revoke'}</button>
                    </form>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      <div className="asym">
        <ConnectDevice />
        <div className="margin-col">
          <span className="kicker">What your kids see</span>
          <p>
            A small badge in the browser whenever it&rsquo;s on, and a plain message when
            a conversation has been sent to you. That disclosure can&rsquo;t be turned
            off.
          </p>
        </div>
      </div>
    </main>
  );
}
