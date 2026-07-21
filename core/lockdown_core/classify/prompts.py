"""Category-specific classifier prompts (design doc §4.3).

Both tiers share the same judgment schema (``ClassifierJudgment``); they differ
in model (Haiku vs Opus) and framing (recall-biased vs precise/verifying). The
prompt is deliberately narrow to ONE category — we never ask a generic "is this
unsafe?" question (design doc §2, §4.2).

The prompts encode the load-bearing distinction: ``directed_at`` separates a real
threat from a book report or a fictional scene. The model supplies judgment axes
only; it never chooses the action (that is derived in ``contract.actions``).
"""

from __future__ import annotations

from lockdown_core.classify.types import ClassifierJudgment
from lockdown_core.contract.verdict import Category, Stage, Turn

_SHARED_GUIDANCE = """\
You are a safety classifier for the category VIOLENCE_TO_OTHERS: a conversation \
plausibly indicating a real intent to physically harm other people.

You are given a rolling window of recent turns from a chatbot conversation. Judge \
the CONVERSATION as a whole, not a single line. Output a structured judgment.

Field guidance:
- directed_at: OTHERS if the potential harm targets real other people; SELF if \
directed at the author themselves; FICTIONAL_OR_ACADEMIC if it is clearly a story, \
essay, game, history question, or hypothetical with no real-world target; \
AMBIGUOUS if you genuinely cannot tell. This is the most important field — an \
essay about WWII or a novel's villain is FICTIONAL_OR_ACADEMIC, not OTHERS.
- severity: how bad the outcome would be if the intent were real.
- confidence: your calibrated probability (0-1) that this is a real intent to harm \
others. Be honest; do not inflate.
- imminence: NONE, SPECULATIVE (idle/venting), DEVELOPING (forming a plan), or \
IMMINENT (specific target/time/means).
- rationale: one or two sentences a human reviewer can act on.
- evidence_spans: character offsets into the relevant user turn(s).

Do not decide what action to take — only describe what you observe."""

_TIER1_SUFFIX = """\

You are the fast FIRST-PASS screen. Bias toward RECALL: if there is a plausible \
real-world threat to others, do not clear it — a human and a second pass will \
verify. Only clear (FICTIONAL_OR_ACADEMIC / low confidence) when it is clearly benign."""

_TIER2_SUFFIX = """\

You are the PRECISE VERIFYING pass behind a lock that has already been applied. \
Weigh the full context carefully and calibrate confidence honestly. Your judgment \
gates whether a responsible adult is notified, so a false alarm here has real cost \
— but a missed real threat is worse. Distinguish genuine intent from venting, dark \
humor, fiction, and academic discussion."""


def system_prompt(*, tier: Stage, category: Category) -> str:
    if category is not Category.VIOLENCE_TO_OTHERS:
        raise ValueError(f"No prompt for category {category!r}")
    suffix = _TIER1_SUFFIX if tier is Stage.TIER1 else _TIER2_SUFFIX
    return _SHARED_GUIDANCE + suffix


def render_window(window: list[Turn]) -> str:
    """Render the rolling window as a transcript for the classifier."""
    lines = [f"[{t.role.upper()}] {t.text}" for t in window]
    return "\n".join(lines)


# Re-exported so callers can reference the output schema in one place.
JUDGMENT_SCHEMA = ClassifierJudgment
