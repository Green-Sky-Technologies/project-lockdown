"""NotificationDispatcher: channel routing, recipient resolution, and the
never-raises guarantee (notification must not break classify)."""

import asyncio

from lockdown_core.contract.verdict import (
    CaptureSurface,
    Category,
    Context,
    DirectedAt,
    EvidenceSpan,
    Imminence,
    RecommendedAction,
    Severity,
    Stage,
    Status,
    Verdict,
)
from lockdown_core.notify.base import NotificationResult
from lockdown_core.notify.dispatcher import NotificationDispatcher


def _verdict() -> Verdict:
    return Verdict(
        verdict_id="22222222-2222-4222-8222-222222222222",
        created_at="2026-08-26T12:00:00+00:00",
        stage=Stage.TIER2,
        status=Status.CONFIRMED,
        category=Category.VIOLENCE_TO_OTHERS,
        directed_at=DirectedAt.OTHERS,
        severity=Severity.HIGH,
        confidence=0.9,
        imminence=Imminence.DEVELOPING,
        recommended_action=RecommendedAction.LOCK_AND_NOTIFY,
        rationale="Targeting a named peer.",
        evidence_spans=[EvidenceSpan(start=0, end=10, turn_index=0)],
        context=Context(
            window_turn_count=3,
            chatbot_host="chatgpt.com",
            capture_surface=CaptureSurface.CHROMIUM_EXT,
            monitored_categories=[Category.VIOLENCE_TO_OTHERS],
        ),
    )


class RecordingNotifier:
    channel = "email"

    def __init__(self, *, delivered: bool = True, raises: bool = False) -> None:
        self.sent: list[tuple[str, str]] = []  # (verdict_id, recipient)
        self._delivered = delivered
        self._raises = raises

    async def send(self, verdict, *, recipient):
        if self._raises:
            raise RuntimeError("notifier exploded")
        self.sent.append((verdict.verdict_id, recipient))
        return NotificationResult(delivered=self._delivered, channel=self.channel, detail="x")


class FakePrefs:
    def __init__(self, channel: str, *, raises: bool = False) -> None:
        self._channel = channel
        self._raises = raises

    async def get(self, *, clerk_user_id, clerk_org_id=None):
        if self._raises:
            raise RuntimeError("db down")
        return self._channel


async def _resolver_ok(clerk_user_id: str) -> str | None:
    return "parent@example.com"


async def _resolver_none(clerk_user_id: str) -> str | None:
    return None


def _dispatch(dispatcher: NotificationDispatcher) -> None:
    asyncio.run(dispatcher.dispatch(_verdict(), clerk_user_id="user_parent"))


def test_email_channel_sends_to_resolved_address():
    notifier = RecordingNotifier()
    _dispatch(
        NotificationDispatcher(
            notifier=notifier, prefs=FakePrefs("email"), resolve_email=_resolver_ok
        )
    )
    assert notifier.sent == [("22222222-2222-4222-8222-222222222222", "parent@example.com")]


def test_dashboard_only_channel_does_not_send():
    notifier = RecordingNotifier()
    _dispatch(
        NotificationDispatcher(
            notifier=notifier, prefs=FakePrefs("dashboard_only"), resolve_email=_resolver_ok
        )
    )
    assert notifier.sent == []


def test_missing_prefs_repo_defaults_to_dashboard_only():
    notifier = RecordingNotifier()
    _dispatch(NotificationDispatcher(notifier=notifier, prefs=None, resolve_email=_resolver_ok))
    assert notifier.sent == []


def test_unresolvable_email_does_not_send():
    notifier = RecordingNotifier()
    _dispatch(
        NotificationDispatcher(
            notifier=notifier, prefs=FakePrefs("email"), resolve_email=_resolver_none
        )
    )
    assert notifier.sent == []


def test_prefs_failure_is_swallowed():
    notifier = RecordingNotifier()
    _dispatch(
        NotificationDispatcher(
            notifier=notifier, prefs=FakePrefs("email", raises=True), resolve_email=_resolver_ok
        )
    )
    assert notifier.sent == []  # returned quietly — never raised


def test_notifier_failure_is_swallowed():
    _dispatch(
        NotificationDispatcher(
            notifier=RecordingNotifier(raises=True),
            prefs=FakePrefs("email"),
            resolve_email=_resolver_ok,
        )
    )  # reaching here without an exception IS the assertion
