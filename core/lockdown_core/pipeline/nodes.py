"""Async pipeline nodes (design doc §7) — real signatures, STUBBED bodies.

These are the stages of the feedback & learning loop. Wired into a LangGraph
``StateGraph`` in ``graph.py`` but not yet implemented — each records that it ran
so the topology is observable end-to-end. Implementing these is post-skeleton
work (see the TODOs and the design doc sections named in each docstring).
"""

from __future__ import annotations

import logging
from typing import Annotated, TypedDict
from operator import add

logger = logging.getLogger("lockdown.pipeline")


class PipelineState(TypedDict, total=False):
    """State threaded through the async pipeline for one confirmed verdict."""

    verdict: dict            # the CONFIRMED verdict (serialized)
    needs_human: bool        # triage decision
    deidentified_text: str | None
    stored: bool
    log: Annotated[list[str], add]   # append-only trace of stages that ran


def triage(state: PipelineState) -> PipelineState:
    """Decide the route (design doc §7: "(if ambiguous) escalate...").

    A confirmed OTHERS verdict routes straight to de-id + store; an AMBIGUOUS or
    lower-confidence one is queued for human review first.
    """
    v = state["verdict"]
    needs_human = v.get("directed_at") == "AMBIGUOUS" or v.get("confidence", 0) < 0.8
    logger.info("pipeline.triage verdict=%s needs_human=%s", v.get("verdict_id"), needs_human)
    return {"needs_human": needs_human, "log": ["triage"]}


def human_review(state: PipelineState) -> PipelineState:
    """Route to an expert reviewer; their CONFIRM/OVERTURN is ground truth (§7).

    TODO: enqueue into the school triage queue / reviewer tooling and await the
    ``review`` block. For now, record that review would occur.
    """
    logger.info("pipeline.human_review (stub) verdict=%s", state["verdict"].get("verdict_id"))
    return {"log": ["human_review"]}


def de_identify(state: PipelineState) -> PipelineState:
    """Real de-identification, not field-stripping (design doc §8).

    TODO: emit a de-identified REWRITE that preserves linguistic signal while
    dropping names/school/teacher/etc. (LLM rewrite and/or clinical de-id tooling
    like Philter/i2b2). Store the rewrite, never raw text.
    """
    logger.info("pipeline.de_identify (stub) verdict=%s", state["verdict"].get("verdict_id"))
    return {"deidentified_text": None, "log": ["de_identify"]}


def feedback_store(state: PipelineState) -> PipelineState:
    """Persist the de-identified, holdout-tagged result to the feedback store (§7).

    TODO: write to the feedback store honoring privacy.retain_as_training and the
    holdout flag. Imminent real-threat cases likely must NOT sit in a training
    corpus (design doc §8, §11).
    """
    logger.info("pipeline.feedback_store (stub) verdict=%s", state["verdict"].get("verdict_id"))
    return {"stored": True, "log": ["feedback_store"]}


def wordlist_maintenance(state: PipelineState) -> PipelineState:
    """Feed the recall-gate wordlist from confirmed/overturned outcomes (§4.2).

    TODO: update per-term fire-rate vs confirm-rate; surface terms that fire and
    never confirm for removal. The wordlist and this pipeline are one loop.
    """
    logger.info("pipeline.wordlist_maintenance (stub) verdict=%s", state["verdict"].get("verdict_id"))
    return {"log": ["wordlist_maintenance"]}
