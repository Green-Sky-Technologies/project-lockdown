"""FastAPI app — the composition root.

Wires the classifier (real Anthropic SDK, or the deterministic fake when no key),
the notifier stub, and the async pipeline. Keeps the hot path a thin
``text in → verdict out`` HTTP surface.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lockdown_core.classify.service import ClassificationService
from lockdown_core.classify.types import Classifier
from lockdown_core.contract.actions import Thresholds
from lockdown_core.contract.verdict import ClassifyRequest, Verdict
from lockdown_core.notify.stub import LoggingNotifier
from lockdown_core.pipeline.base import NoOpPipeline, PipelineRunner
from lockdown_core.settings import Settings, get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lockdown.app")


def _build_classifier(settings: Settings) -> Classifier:
    if settings.use_fake_classifier or not settings.anthropic_api_key:
        logger.warning("Using FAKE classifier (no ANTHROPIC_API_KEY or fake forced).")
        from lockdown_core.classify.fake import FakeClassifier

        return FakeClassifier()
    # Real tier-1/tier-2 Anthropic classifier (M3).
    from lockdown_core.classify.anthropic_classifier import AnthropicClassifier

    return AnthropicClassifier(settings)


def _build_pipeline(settings: Settings) -> PipelineRunner:
    if not settings.use_langgraph_pipeline:
        return NoOpPipeline()
    # Imported lazily HERE (the composition root) so langgraph never lands on the
    # classifier hot-path import graph (design doc §4.3).
    from lockdown_core.pipeline.graph import LangGraphPipeline

    return LangGraphPipeline()


def build_service(settings: Settings | None = None) -> ClassificationService:
    settings = settings or get_settings()
    return ClassificationService(
        classifier=_build_classifier(settings),
        notifier=LoggingNotifier(),
        pipeline=_build_pipeline(settings),
        thresholds=Thresholds(
            high_confidence=settings.high_confidence,
            log_confidence=settings.log_confidence,
        ),
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Project Lockdown — Detection Core",
        version="0.1.0",
        summary="Stateless classifier that emits the verdict contract (design doc §5).",
    )

    # The extension calls this cross-origin from the chatbot page.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten to specific chatbot origins in production
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )

    service = build_service(settings)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "version": app.version}

    @app.post("/classify", response_model=Verdict, response_model_exclude_none=False)
    async def classify(req: ClassifyRequest) -> Verdict:
        # Defensive cap on window size (§4: proportionate capture).
        if len(req.windowed_text) > settings.max_window_turns:
            req = req.model_copy(
                update={"windowed_text": req.windowed_text[-settings.max_window_turns :]}
            )
        return await service.classify(req)

    return app


app = create_app()
