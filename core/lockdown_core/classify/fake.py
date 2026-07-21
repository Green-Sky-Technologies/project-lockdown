"""A deterministic, keyless classifier for tests and offline dev.

NOT a safety classifier — a transparent keyword heuristic that lets the whole
pipeline run end-to-end without an API key. Its judgments are shaped so the
§5.3 action table is exercised. Selected with ``LOCKDOWN_USE_FAKE_CLASSIFIER=1``
(or automatically when no ``ANTHROPIC_API_KEY`` is present).
"""

from __future__ import annotations

from lockdown_core.classify.types import ClassifierJudgment
from lockdown_core.contract.verdict import (
    Category,
    DirectedAt,
    EvidenceSpan,
    Imminence,
    Severity,
    Stage,
    Turn,
)

_FICTIONAL = ("essay", "homework", "novel", "history", "wwii", "world war", "for my book", "story", "movie", "video game")
_SELF = ("myself", "my own life", "suicide", "kill myself", "end it all")
_OTHERS = ("kill", "shoot", "hurt", "attack", "stab", "bomb", "beat up", "get rid of")
_IMMINENT = ("tomorrow", "tonight", "today", "after school", "at 3", "this week", "bring the")
_DEVELOPING = ("planning", "figured out", "i will", "i'm going to", "map of", "schedule")


def _user_text(window: list[Turn]) -> str:
    return "\n".join(t.text for t in window if t.role == "user").lower()


class FakeClassifier:
    """Implements the ``Classifier`` protocol."""

    async def judge(
        self,
        *,
        tier: Stage,
        window: list[Turn],
        category: Category,
    ) -> ClassifierJudgment:
        text = _user_text(window)

        has_others = any(k in text for k in _OTHERS)
        has_self = any(k in text for k in _SELF)
        has_fiction = any(k in text for k in _FICTIONAL)

        if has_fiction and not (has_others or has_self):
            return ClassifierJudgment(
                directed_at=DirectedAt.FICTIONAL_OR_ACADEMIC,
                severity=Severity.LOW,
                confidence=0.2,
                imminence=Imminence.NONE,
                rationale="Reads as academic/fictional framing; no real-world target.",
            )

        if has_self and not has_others:
            return ClassifierJudgment(
                directed_at=DirectedAt.SELF,
                severity=Severity.HIGH,
                confidence=0.6,
                imminence=Imminence.SPECULATIVE,
                rationale="Language directed at self; routes differently by design.",
            )

        if has_others:
            imminence = (
                Imminence.IMMINENT
                if any(k in text for k in _IMMINENT)
                else Imminence.DEVELOPING
                if any(k in text for k in _DEVELOPING)
                else Imminence.SPECULATIVE
            )
            # Fiction words alongside real-target language make it ambiguous.
            directed = DirectedAt.AMBIGUOUS if has_fiction else DirectedAt.OTHERS
            # Tier-2 is the "precise/verifying" pass; give it a firmer read.
            confidence = 0.9 if tier == Stage.TIER2 else 0.75
            severity = Severity.CRITICAL if imminence == Imminence.IMMINENT else Severity.HIGH
            idx = next((i for i, t in enumerate(window) if t.role == "user"), 0)
            return ClassifierJudgment(
                directed_at=directed,
                severity=severity,
                confidence=confidence if directed == DirectedAt.OTHERS else 0.5,
                imminence=imminence,
                rationale="Mentions harm toward another; "
                + ("academic framing muddies intent." if has_fiction else "target and intent language present."),
                evidence_spans=[EvidenceSpan(start=0, end=min(len(window[idx].text), 80), turn_index=idx)],
            )

        return ClassifierJudgment(
            directed_at=DirectedAt.AMBIGUOUS,
            severity=Severity.MODERATE,
            confidence=0.4,
            imminence=Imminence.SPECULATIVE,
            rationale="Recall gate fired but intent is unclear from the window.",
        )
