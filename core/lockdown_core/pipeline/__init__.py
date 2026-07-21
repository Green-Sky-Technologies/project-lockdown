"""Async feedback & learning pipeline (design doc §7).

IMPORTANT: this package pulls in LangGraph, which must never touch the classifier
hot path. The classifier depends only on the ``PipelineRunner`` protocol in
``pipeline.base`` (no LangGraph import); the concrete ``LangGraphPipeline`` in
``pipeline.graph`` is wired at the composition root (``app.py``). Do NOT import
``pipeline.graph`` from ``__init__`` or the classify path — an architecture test
enforces this.
"""

from lockdown_core.pipeline.base import NoOpPipeline, PipelineRunner

__all__ = ["NoOpPipeline", "PipelineRunner"]
