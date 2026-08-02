'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import type { DeviceToken } from '@/lib/core';
import { createTokenAction, revokeTokenAction } from './actions';

export function DeviceTokens({ initial }: { initial: DeviceToken[] }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [name, setName] = useState('');
  const [freshToken, setFreshToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const generate = () => {
    startTransition(async () => {
      const { token } = await createTokenAction(name);
      setFreshToken(token);
      setCopied(false);
      setName('');
      router.refresh();
    });
  };

  const revoke = (id: string) => {
    startTransition(async () => {
      await revokeTokenAction(id);
      router.refresh();
    });
  };

  const copy = async () => {
    if (!freshToken) return;
    await navigator.clipboard.writeText(freshToken);
    setCopied(true);
  };

  const active = initial.filter((t) => !t.revoked);

  return (
    <div>
      <div className="token-generate">
        <input
          className="token-name"
          placeholder="Device name (e.g. Emma's Chromebook)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={pending}
        />
        <button className="button" onClick={generate} disabled={pending}>
          {pending ? 'Working…' : 'Generate token'}
        </button>
      </div>

      {freshToken && (
        <div className="token-reveal">
          <p className="small">
            <strong>Copy this now — it won’t be shown again.</strong> Paste it into the
            extension popup.
          </p>
          <div className="token-value">
            <code>{freshToken}</code>
            <button className="button-sm" onClick={copy}>
              {copied ? 'Copied ✓' : 'Copy'}
            </button>
          </div>
        </div>
      )}

      <h2>Your devices</h2>
      {active.length === 0 ? (
        <p className="empty">No connected devices yet.</p>
      ) : (
        <table className="verdicts">
          <thead>
            <tr>
              <th>Name</th>
              <th>Created</th>
              <th>Last used</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {active.map((t) => (
              <tr key={t.id}>
                <td>{t.name || '(unnamed)'}</td>
                <td>{new Date(t.created_at).toLocaleDateString()}</td>
                <td>{t.last_used_at ? new Date(t.last_used_at).toLocaleString() : 'never'}</td>
                <td>
                  <button className="button-sm danger" onClick={() => revoke(t.id)} disabled={pending}>
                    Revoke
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
