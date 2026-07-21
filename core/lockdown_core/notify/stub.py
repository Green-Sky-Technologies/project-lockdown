"""Logging notifier — the skeleton's stand-in for Resend/Twilio.

Logs the rendered payload instead of sending. Swap for a real ``Notifier`` (same
protocol) once providers are wired; no call sites change.
"""

from __future__ import annotations

import logging

from lockdown_core.contract.verdict import Verdict
from lockdown_core.notify.base import NotificationResult, render_notification

logger = logging.getLogger("lockdown.notify")


class LoggingNotifier:
    """Implements the ``Notifier`` protocol; delivers to the log."""

    channel = "log"

    async def send(self, verdict: Verdict, *, recipient: str) -> NotificationResult:
        body = render_notification(verdict)
        logger.warning(
            "STUB NOTIFY -> %s (verdict=%s action=%s)\n%s",
            recipient,
            verdict.verdict_id,
            verdict.recommended_action.value,
            body,
        )
        return NotificationResult(delivered=True, channel=self.channel, detail=body)
