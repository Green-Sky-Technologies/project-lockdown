"""ResendNotifier: payload shape, subject urgency, and failure isolation.

All HTTP is intercepted with ``httpx.MockTransport`` — no network, no key. The
notifier must never raise: transport errors and non-2xx responses come back as
``delivered=False`` results (§6: best-effort delivery).
"""

import asyncio
import json

import httpx

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
from lockdown_core.notify.base import CRISIS_GUIDANCE
from lockdown_core.notify.resend import ResendNotifier


def _verdict(**over) -> Verdict:
    base = dict(
        verdict_id="11111111-1111-4111-8111-111111111111",
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
    base.update(over)
    return Verdict(**base)


def _notifier(handler) -> tuple[ResendNotifier, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return (
        ResendNotifier(api_key="re_test_key", from_email="onboarding@resend.dev", client=client),
        client,
    )


def test_success_payload_and_message_id():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "msg_123"})

    notifier, client = _notifier(handler)

    async def run():
        result = await notifier.send(_verdict(), recipient="parent@example.com")
        await client.aclose()
        return result

    result = asyncio.run(run())
    assert result.delivered is True and result.channel == "email"
    assert "msg_123" in result.detail
    assert seen["auth"] == "Bearer re_test_key"
    p = seen["payload"]
    assert p["from"] == "onboarding@resend.dev"
    assert p["to"] == ["parent@example.com"]
    assert p["subject"].startswith("Project Lockdown")
    assert "(urgent)" not in p["subject"]  # plain LOCK_AND_NOTIFY is not urgent
    assert "flagged for your review" in p["text"]
    assert CRISIS_GUIDANCE not in p["text"]


def test_crisis_action_marks_subject_urgent_and_includes_guidance():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "msg_456"})

    notifier, client = _notifier(handler)

    async def run():
        result = await notifier.send(
            _verdict(
                recommended_action=RecommendedAction.LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES,
                imminence=Imminence.IMMINENT,
            ),
            recipient="parent@example.com",
        )
        await client.aclose()
        return result

    result = asyncio.run(run())
    assert result.delivered is True
    assert seen["payload"]["subject"].endswith("(urgent)")
    assert CRISIS_GUIDANCE in seen["payload"]["text"]


def test_api_error_returns_undelivered_without_raising():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"message": "invalid from"})

    notifier, client = _notifier(handler)

    async def run():
        result = await notifier.send(_verdict(), recipient="parent@example.com")
        await client.aclose()
        return result

    result = asyncio.run(run())
    assert result.delivered is False
    assert "422" in result.detail


def test_transport_error_returns_undelivered_without_raising():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    notifier, client = _notifier(handler)

    async def run():
        result = await notifier.send(_verdict(), recipient="parent@example.com")
        await client.aclose()
        return result

    result = asyncio.run(run())
    assert result.delivered is False
    assert "transport error" in result.detail
