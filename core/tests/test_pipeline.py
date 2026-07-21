"""LangGraph async pipeline (design doc §7): topology + branching + runner.

Uses ``asyncio.run`` directly (no pytest-asyncio dependency).
"""

import asyncio

from lockdown_core.pipeline.graph import LangGraphPipeline, build_graph
from lockdown_core.contract.verdict import (
    Category,
    Context,
    CaptureSurface,
    DirectedAt,
    Imminence,
    RecommendedAction,
    Severity,
    Stage,
    Status,
    Verdict,
)

CFG = {"configurable": {"thread_id": "t-test"}}


def _run(verdict_dict):
    graph = build_graph()
    return asyncio.run(graph.ainvoke({"verdict": verdict_dict, "log": []}, config=CFG))


def test_confirmed_others_skips_human_review():
    state = _run({"verdict_id": "v1", "directed_at": "OTHERS", "confidence": 0.9})
    assert state["needs_human"] is False
    assert state["log"] == ["triage", "de_identify", "feedback_store", "wordlist_maintenance"]
    assert state["stored"] is True


def test_ambiguous_routes_through_human_review():
    state = _run({"verdict_id": "v2", "directed_at": "AMBIGUOUS", "confidence": 0.5})
    assert state["needs_human"] is True
    assert state["log"] == [
        "triage",
        "human_review",
        "de_identify",
        "feedback_store",
        "wordlist_maintenance",
    ]


def test_low_confidence_others_still_reviewed():
    state = _run({"verdict_id": "v3", "directed_at": "OTHERS", "confidence": 0.6})
    assert state["needs_human"] is True
    assert "human_review" in state["log"]


def test_runner_completes_on_confirmed_verdict():
    verdict = Verdict(
        verdict_id="33333333-3333-4333-8333-333333333333",
        created_at="2026-07-01T12:00:00Z",
        stage=Stage.TIER2,
        status=Status.CONFIRMED,
        category=Category.VIOLENCE_TO_OTHERS,
        directed_at=DirectedAt.OTHERS,
        severity=Severity.HIGH,
        confidence=0.9,
        imminence=Imminence.DEVELOPING,
        recommended_action=RecommendedAction.LOCK_AND_NOTIFY,
        rationale="Confirmed threat toward a named peer.",
        context=Context(
            window_turn_count=4,
            chatbot_host="chatgpt.com",
            capture_surface=CaptureSurface.CHROMIUM_EXT,
            monitored_categories=[Category.VIOLENCE_TO_OTHERS],
        ),
    )
    # Should complete without raising.
    asyncio.run(LangGraphPipeline().run(verdict))
