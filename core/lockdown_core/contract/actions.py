"""Verdict → ``recommended_action`` derivation (design doc §5.3).

This is the ONE place the thresholds live. Every surface (lock logic,
notifications, dashboard) acts on the computed ``recommended_action`` rather than
re-deriving thresholds independently (design doc §5.1). The model never chooses
the action — it only supplies ``directed_at`` / ``imminence`` / ``confidence`` and
this function maps them.

Two load-bearing principles are encoded here:

* **Verified before alert (§1):** no notification fires on the recall gate or
  tier-1 alone. A NOTIFY-class action computed at ``RECALL_GATE``/``TIER1`` is
  downgraded to ``LOCK`` (locked pending review) until tier-2/human confirms.
* **Self-directed content does not auto-notify (§5.3):** ``SELF_HARM`` is not a
  v1 category and routes differently by design; if this violence classifier ever
  emits ``directed_at == SELF`` we log only — never auto-alert an adult.
"""

from __future__ import annotations

from dataclasses import dataclass

from lockdown_core.contract.verdict import (
    Category,
    DirectedAt,
    Imminence,
    RecommendedAction,
    Stage,
)

# Ordinal ranking for "≤ DEVELOPING" style comparisons.
_IMMINENCE_ORDER: dict[Imminence, int] = {
    Imminence.NONE: 0,
    Imminence.SPECULATIVE: 1,
    Imminence.DEVELOPING: 2,
    Imminence.IMMINENT: 3,
}

_NOTIFY_ACTIONS = frozenset(
    {
        RecommendedAction.LOCK_AND_NOTIFY,
        RecommendedAction.LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES,
    }
)

_UNVERIFIED_STAGES = frozenset({Stage.RECALL_GATE, Stage.TIER1})


@dataclass(frozen=True)
class Thresholds:
    """Tunable cut points. Sourced from settings in the service; defaults here
    keep :func:`derive_action` pure and unit-testable."""

    high_confidence: float = 0.7
    log_confidence: float = 0.3


DEFAULT_THRESHOLDS = Thresholds()


def _imminence_at_most(imminence: Imminence, ceiling: Imminence) -> bool:
    return _IMMINENCE_ORDER[imminence] <= _IMMINENCE_ORDER[ceiling]


def _base_action(
    *,
    directed_at: DirectedAt,
    imminence: Imminence,
    confidence: float,
    t: Thresholds,
) -> RecommendedAction:
    """The §5.3 table for VIOLENCE_TO_OTHERS, ignoring the verified-before-alert
    stage gate (applied separately in :func:`derive_action`)."""
    high = confidence >= t.high_confidence

    if directed_at is DirectedAt.FICTIONAL_OR_ACADEMIC:
        # Book-report / essay. Keep low-signal ones out of the store entirely;
        # log the rest for wordlist confirm-rate health (§4.2, §9).
        return (
            RecommendedAction.LOG_ONLY
            if confidence >= t.log_confidence
            else RecommendedAction.NO_ACTION
        )

    if directed_at is DirectedAt.SELF:
        # Not a v1 category; do NOT auto-notify (§5.3). Log for governance only.
        return RecommendedAction.LOG_ONLY

    if directed_at is DirectedAt.AMBIGUOUS:
        # Lock pending review; never notify on an ambiguous read.
        return RecommendedAction.LOCK

    # directed_at is OTHERS
    if high and imminence is Imminence.IMMINENT:
        return RecommendedAction.LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES
    if high and _imminence_at_most(imminence, Imminence.DEVELOPING):
        return RecommendedAction.LOCK_AND_NOTIFY
    # Directed at others but not confident enough to notify: lock pending review.
    return RecommendedAction.LOCK


def derive_action(
    *,
    category: Category,
    directed_at: DirectedAt,
    imminence: Imminence,
    confidence: float,
    stage: Stage,
    thresholds: Thresholds = DEFAULT_THRESHOLDS,
) -> RecommendedAction:
    """Map a (category, directed_at, imminence, confidence, stage) tuple to the
    single computed action every surface renders from."""
    if category is not Category.VIOLENCE_TO_OTHERS:
        # No other category is live in v1; refuse rather than guess.
        raise ValueError(f"No action mapping for category {category!r}")

    action = _base_action(
        directed_at=directed_at,
        imminence=imminence,
        confidence=confidence,
        t=thresholds,
    )

    # Verified before alert (§1): downgrade any notify to a bare lock until a
    # tier-2/human stage has confirmed.
    if stage in _UNVERIFIED_STAGES and action in _NOTIFY_ACTIONS:
        return RecommendedAction.LOCK

    return action


# Actions at/above which the extension renders the lock overlay.
def crosses_lock_threshold(action: RecommendedAction) -> bool:
    return action not in (RecommendedAction.NO_ACTION, RecommendedAction.LOG_ONLY)


def triggers_notification(action: RecommendedAction) -> bool:
    return action in _NOTIFY_ACTIONS
