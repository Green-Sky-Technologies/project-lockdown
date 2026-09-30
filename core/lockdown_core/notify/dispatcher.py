"""Notification dispatch — prefs → recipient → channel, off the response path.

Runs as a FastAPI background task after ``/classify`` returns a CONFIRMED verdict
whose action notifies (§1: verified before alert). Mirrors the persistence
posture: everything here is best-effort and must NEVER propagate an exception
back toward the lock decision.

Imports only the protocol seam (``notify.base``) + stdlib; the concrete prefs
repo, Clerk email resolver, and Resend notifier are injected at the composition
root so this module stays clean of heavy deps.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Protocol

from lockdown_core.contract.verdict import Verdict
from lockdown_core.notify.base import Notifier

logger = logging.getLogger("lockdown.notify")

CHANNEL_DASHBOARD_ONLY = "dashboard_only"
CHANNEL_EMAIL = "email"

# clerk_user_id -> email address (None when unresolvable).
EmailResolver = Callable[[str], Awaitable[str | None]]


class ChannelPrefs(Protocol):
    async def get(self, *, clerk_user_id: str, clerk_org_id: str | None = None) -> str: ...


class NotificationDispatcher:
    def __init__(
        self,
        *,
        notifier: Notifier,
        prefs: ChannelPrefs | None,
        resolve_email: EmailResolver,
    ) -> None:
        self._notifier = notifier
        self._prefs = prefs
        self._resolve_email = resolve_email

    async def dispatch(
        self, verdict: Verdict, *, clerk_user_id: str, clerk_org_id: str | None = None
    ) -> None:
        """Route a confirmed notify-verdict to the parent's chosen channel.
        Never raises — notification is best-effort (§6)."""
        try:
            channel = CHANNEL_DASHBOARD_ONLY
            if self._prefs is not None:
                channel = await self._prefs.get(
                    clerk_user_id=clerk_user_id, clerk_org_id=clerk_org_id
                )

            if channel != CHANNEL_EMAIL:
                # The persisted verdict IS the dashboard notification.
                logger.info(
                    "verdict %s routed to dashboard only (channel=%s)",
                    verdict.verdict_id,
                    channel,
                )
                return

            email = await self._resolve_email(clerk_user_id)
            if not email:
                logger.warning(
                    "verdict %s: no email resolvable for account — not delivered",
                    verdict.verdict_id,
                )
                return

            result = await self._notifier.send(verdict, recipient=email)
            if result.delivered:
                # No body/rationale in the success log (§8: privacy-minimal logs).
                logger.info(
                    "verdict %s delivered via %s (%s)",
                    verdict.verdict_id,
                    result.channel,
                    result.detail,
                )
            else:
                logger.warning(
                    "verdict %s delivery FAILED via %s: %s",
                    verdict.verdict_id,
                    result.channel,
                    result.detail,
                )
        except Exception:  # noqa: BLE001 — notification must never break classify
            logger.exception("failed to dispatch notification for verdict %s", verdict.verdict_id)
