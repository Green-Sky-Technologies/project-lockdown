"""The §5.3 VIOLENCE_TO_OTHERS action table, encoded as executable cases.

Confidence 0.9 == "high" (>= 0.7 default); 0.2 == "not high".
"""

import pytest

from lockdown_core.contract.actions import (
    crosses_lock_threshold,
    derive_action,
    triggers_notification,
)
from lockdown_core.contract.verdict import (
    Category,
    DirectedAt,
    Imminence,
    RecommendedAction,
    Stage,
)

V = Category.VIOLENCE_TO_OTHERS
A = RecommendedAction


# (directed_at, imminence, confidence, stage) -> expected action
CASES = [
    # FICTIONAL_OR_ACADEMIC: any imminence/confidence -> NO_ACTION / LOG_ONLY, never locks.
    (DirectedAt.FICTIONAL_OR_ACADEMIC, Imminence.IMMINENT, 0.9, Stage.TIER2, A.LOG_ONLY),
    (DirectedAt.FICTIONAL_OR_ACADEMIC, Imminence.NONE, 0.1, Stage.TIER2, A.NO_ACTION),
    # AMBIGUOUS (<= DEVELOPING): LOCK pending review, no notify — at any confidence.
    (DirectedAt.AMBIGUOUS, Imminence.DEVELOPING, 0.95, Stage.TIER2, A.LOCK),
    (DirectedAt.AMBIGUOUS, Imminence.SPECULATIVE, 0.2, Stage.TIER2, A.LOCK),
    # OTHERS + <= DEVELOPING + high confidence, confirmed -> LOCK_AND_NOTIFY.
    (DirectedAt.OTHERS, Imminence.DEVELOPING, 0.9, Stage.TIER2, A.LOCK_AND_NOTIFY),
    # OTHERS + IMMINENT + high confidence, confirmed -> crisis resources.
    (DirectedAt.OTHERS, Imminence.IMMINENT, 0.9, Stage.TIER2, A.LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES),
    # OTHERS but not high confidence -> LOCK (pending), never notify.
    (DirectedAt.OTHERS, Imminence.DEVELOPING, 0.2, Stage.TIER2, A.LOCK),
    # SELF is not a v1 category and must never auto-notify (§5.3).
    (DirectedAt.SELF, Imminence.IMMINENT, 0.99, Stage.TIER2, A.LOG_ONLY),
]


@pytest.mark.parametrize("directed_at,imminence,confidence,stage,expected", CASES)
def test_action_table(directed_at, imminence, confidence, stage, expected):
    assert (
        derive_action(
            category=V,
            directed_at=directed_at,
            imminence=imminence,
            confidence=confidence,
            stage=stage,
        )
        == expected
    )


def test_verified_before_alert_downgrades_notify_on_tier1():
    """Principle §1: a would-be notify at tier-1 is downgraded to a bare LOCK."""
    tier1 = derive_action(
        category=V,
        directed_at=DirectedAt.OTHERS,
        imminence=Imminence.IMMINENT,
        confidence=0.95,
        stage=Stage.TIER1,
    )
    assert tier1 == A.LOCK
    assert not triggers_notification(tier1)

    # Same inputs, confirmed at tier-2, DO notify.
    tier2 = derive_action(
        category=V,
        directed_at=DirectedAt.OTHERS,
        imminence=Imminence.IMMINENT,
        confidence=0.95,
        stage=Stage.TIER2,
    )
    assert tier2 == A.LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES
    assert triggers_notification(tier2)


def test_recall_gate_never_notifies():
    action = derive_action(
        category=V,
        directed_at=DirectedAt.OTHERS,
        imminence=Imminence.DEVELOPING,
        confidence=0.99,
        stage=Stage.RECALL_GATE,
    )
    assert action == A.LOCK


def test_lock_threshold_helpers():
    assert not crosses_lock_threshold(A.NO_ACTION)
    assert not crosses_lock_threshold(A.LOG_ONLY)
    assert crosses_lock_threshold(A.LOCK)
    assert crosses_lock_threshold(A.LOCK_AND_NOTIFY)


def test_unknown_category_refuses():
    class _Fake:
        pass

    with pytest.raises(ValueError):
        derive_action(
            category=_Fake(),  # type: ignore[arg-type]
            directed_at=DirectedAt.OTHERS,
            imminence=Imminence.NONE,
            confidence=0.5,
            stage=Stage.TIER2,
        )
