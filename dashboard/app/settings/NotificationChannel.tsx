'use client';

import { useState, useTransition } from 'react';
import { setNotificationChannelAction } from './actions';
import type { NotifyChannel } from '@/lib/core';

/**
 * The "How we reach you" radio group. Email + dashboard are live against the
 * core's /notification-settings; SMS stays a disabled affordance until Twilio
 * is wired. Selection is optimistic — a failed save rolls back to the last
 * confirmed channel.
 */
export function NotificationChannel({
  initial,
  email,
  disabled = false,
}: {
  initial: NotifyChannel;
  email?: string;
  disabled?: boolean;
}) {
  const [channel, setChannel] = useState<NotifyChannel>(initial);
  const [pending, startTransition] = useTransition();

  const choose = (next: 'dashboard_only' | 'email') => {
    if (disabled || pending || next === channel) return;
    const previous = channel;
    setChannel(next);
    startTransition(async () => {
      try {
        await setNotificationChannelAction(next);
      } catch {
        setChannel(previous);
      }
    });
  };

  const row = (
    key: 'dashboard_only' | 'email',
    label: string,
    caption: string,
  ) => (
    <div
      className={`radio-row${disabled ? ' is-disabled' : ''}`}
      role="radio"
      aria-checked={channel === key}
      tabIndex={disabled ? -1 : 0}
      style={disabled ? undefined : { cursor: 'pointer' }}
      onClick={() => choose(key)}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && choose(key)}
    >
      <span className={`radio-dot${channel === key ? ' is-checked' : ''}`} />
      <div className="rlabel">
        <span className="rl">{label}</span>
        <span className="rc">{caption}</span>
      </div>
    </div>
  );

  return (
    <div role="radiogroup" aria-label="How we reach you" aria-busy={pending}>
      <div className="radio-row is-disabled">
        <span className="radio-dot" />
        <div className="rlabel">
          <span className="rl">Text me straight away</span>
          <span className="rc">Coming soon</span>
        </div>
      </div>
      {row(
        'email',
        'Email me instead',
        email ? `Alerts go to ${email}` : 'Alerts go to your account email',
      )}
      {row(
        'dashboard_only',
        'Only in the dashboard',
        'Anything that needs you appears here first — nothing arrives on your phone.',
      )}
    </div>
  );
}
