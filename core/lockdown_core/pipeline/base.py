"""Pipeline runner protocol — the seam between the hot path and the async work.

Defined WITHOUT importing LangGraph so the classifier can depend on it while
keeping ``langgraph`` off the hot-path import graph (design doc §4.3).
"""

from __future__ import annotations

import logging
from typing import Protocol

from lockdown_core.contract.verdict import Verdict

logger = logging.getLogger("lockdown.pipeline")


class PipelineRunner(Protocol):
    async def run(self, verdict: Verdict) -> None:
        """Kick off async escalation/review/de-id/feedback for a CONFIRMED verdict."""
        ...


class NoOpPipeline:
    """Default runner: records that a verdict would enter the pipeline.

    Replaced by ``pipeline.graph.LangGraphPipeline`` at the composition root.
    """

    async def run(self, verdict: Verdict) -> None:
        logger.info("NoOp pipeline: verdict %s would enter async pipeline", verdict.verdict_id)
