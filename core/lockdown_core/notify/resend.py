"""Resend email notifier (design doc §6).

Implements the ``Notifier`` protocol over Resend's send-email REST endpoint with
an async httpx POST (the official ``resend`` SDK is sync/requests-based and would
block the event loop). Imported only from the composition root (``app.py``) —
never from ``notify/__init__`` — so httpx stays off the classifier hot path.
"""

from __future__ import annotations

import logging

import httpx

from lockdown_core.contract.verdict import RecommendedAction, Verdict
from lockdown_core.notify.base import NotificationResult, render_notification

logger = logging.getLogger("lockdown.notify")

_RESEND_ENDPOINT = "https://api.resend.com/emails"
_SUBJECT = "Project Lockdown — a conversation was flagged for your review"


class ResendNotifier:
    """Implements the ``Notifier`` protocol; delivers email via Resend.

    Never raises: delivery failure is reported through ``NotificationResult``
    (notification is best-effort §6; the caller decides what to log).
    """

    channel = "email"

    def __init__(
        self,
        *,
        api_key: str,
        from_email: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._from_email = from_email
        self._client = client  # injectable for tests (httpx.MockTransport)

    async def send(self, verdict: Verdict, *, recipient: str) -> NotificationResult:
        subject = _SUBJECT
        if verdict.recommended_action is RecommendedAction.LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES:
            subject += " (urgent)"

        payload = {
            "from": self._from_email,
            "to": [recipient],
            "subject": subject,
            "text": render_notification(verdict),
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            if self._client is not None:
                resp = await self._client.post(_RESEND_ENDPOINT, json=payload, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(_RESEND_ENDPOINT, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            return NotificationResult(
                delivered=False, channel=self.channel, detail=f"transport error: {exc!r}"
            )

        if resp.status_code // 100 != 2:
            return NotificationResult(
                delivered=False,
                channel=self.channel,
                detail=f"resend {resp.status_code}: {resp.text[:200]}",
            )

        message_id = ""
        try:
            message_id = resp.json().get("id", "")
        except ValueError:
            pass
        return NotificationResult(
            delivered=True, channel=self.channel, detail=f"resend id={message_id}"
        )
