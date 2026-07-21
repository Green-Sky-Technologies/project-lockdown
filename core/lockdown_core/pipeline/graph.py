"""LangGraph async pipeline (design doc §7).

THIS is where LangGraph earns its place — latency is irrelevant, state and
durability matter. A ``StateGraph`` with a checkpointer orchestrates the stateful,
branching feedback loop off the hot path. The nodes are stubbed (``nodes.py``);
the topology and state plumbing are real.

    START → triage ─┬─(needs_human)→ human_review ─┐
                    └─────────────────────────────→ de_identify → feedback_store
                                                     → wordlist_maintenance → END

IMPORTANT: this module imports ``langgraph`` and must ONLY be imported at the
composition root (``app.py``), never from the classifier hot path (design doc
§4.3). An architecture test enforces that ``classify.service`` never reaches it.
"""

from __future__ import annotations

import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from lockdown_core.contract.verdict import Verdict
from lockdown_core.pipeline.nodes import (
    PipelineState,
    de_identify,
    feedback_store,
    human_review,
    triage,
    wordlist_maintenance,
)

logger = logging.getLogger("lockdown.pipeline")


def _route_after_triage(state: PipelineState) -> str:
    return "human_review" if state.get("needs_human") else "de_identify"


def build_graph():
    """Compile the async pipeline graph with an in-memory checkpointer."""
    g = StateGraph(PipelineState)
    g.add_node("triage", triage)
    g.add_node("human_review", human_review)
    g.add_node("de_identify", de_identify)
    g.add_node("feedback_store", feedback_store)
    g.add_node("wordlist_maintenance", wordlist_maintenance)

    g.add_edge(START, "triage")
    g.add_conditional_edges("triage", _route_after_triage, ["human_review", "de_identify"])
    g.add_edge("human_review", "de_identify")
    g.add_edge("de_identify", "feedback_store")
    g.add_edge("feedback_store", "wordlist_maintenance")
    g.add_edge("wordlist_maintenance", END)

    # A checkpointer makes the pipeline durable/resumable (design doc §7).
    return g.compile(checkpointer=MemorySaver())


class LangGraphPipeline:
    """Implements the ``PipelineRunner`` protocol. Triggered off a CONFIRMED verdict."""

    def __init__(self) -> None:
        self._graph = build_graph()

    async def run(self, verdict: Verdict) -> None:
        config = {"configurable": {"thread_id": verdict.verdict_id}}
        final = await self._graph.ainvoke(
            {"verdict": verdict.model_dump(mode="json"), "log": []},
            config=config,
        )
        logger.info(
            "pipeline complete verdict=%s stages=%s",
            verdict.verdict_id,
            final.get("log"),
        )
