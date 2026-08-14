'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Copy } from '@phosphor-icons/react';
import { createTokenAction } from './actions';

/**
 * The new-token panel. The plaintext token is only ever available at creation —
 * this mirrors createDeviceToken's one-shot contract: shown once, then gone.
 */
export function ConnectDevice() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [name, setName] = useState('');
  const [fresh, setFresh] = useState<{ name: string; token: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const generate = () => {
    const deviceName = name.trim();
    if (!deviceName) return;
    startTransition(async () => {
      const { token } = await createTokenAction(deviceName);
      setFresh({ name: deviceName, token });
      setCopied(false);
      setName('');
      router.refresh();
    });
  };

  const copy = async () => {
    if (!fresh) return;
    await navigator.clipboard.writeText(fresh.token);
    setCopied(true);
  };

  return (
    <div className="token-panel" id="connect">
      <span className="kicker kicker-accent">
        {fresh ? `New token · ${fresh.name}` : 'Connect a device'}
      </span>
      {fresh ? (
        <>
          <p className="explain">
            Open the extension on that device, choose Connect, and paste this in.
            It&rsquo;s shown once. Revoking it here disconnects the device immediately.
          </p>
          <div className="token-line">
            <span className="token-value">{fresh.token}</span>
            <button className="btn-accent btn-sm" onClick={copy}>
              <Copy size={15} />
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="explain">
            Name the device, create its token, then paste the token into the extension on
            that device. One token per browser.
          </p>
          <div className="token-line">
            <input
              className="token-input"
              placeholder="Device name — e.g. Family iPad"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && generate()}
              disabled={pending}
            />
            <button className="btn-accent btn-sm" onClick={generate} disabled={pending || !name.trim()}>
              {pending ? 'Working…' : 'Create token'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
