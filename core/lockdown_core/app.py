"""FastAPI app — the composition root.

Wires the classifier (real Anthropic SDK, or the deterministic fake when no key),
the notifier stub, and the async pipeline. Keeps the hot path a thin
``text in → verdict out`` HTTP surface.
"""

from __future__ import annotations

import logging
import os

from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lockdown_core.auth.clerk import AuthContext
from lockdown_core.auth.dependencies import build_authorizer, build_clerk_authorizer
from lockdown_core.auth.device_router import build_device_token_router
from lockdown_core.auth.ratelimit import RateLimiter
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


def _build_persistence(settings: Settings):
    """``(verdict_repo, device_token_repo)`` off one Neon engine, or ``(None, None)``.

    The device-token repo is built whenever a ``database_url`` is set (even if
    verdict persistence is off) — extension auth needs it independent of whether
    we're storing verdicts. Imported lazily HERE (composition root) so sqlalchemy
    stays off the classifier hot path."""
    if not settings.database_url:
        return None, None
    from lockdown_core.persistence import (
        DeviceTokenRepository,
        VerdictRepository,
        make_engine,
        make_sessionmaker,
    )

    sessionmaker = make_sessionmaker(make_engine(settings.database_url))
    verdict_repo = VerdictRepository(sessionmaker) if settings.persist_verdicts else None
    return verdict_repo, DeviceTokenRepository(sessionmaker)


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


def apply_langsmith_env(settings: Settings) -> None:
    """Mirror LANGSMITH_* from settings/.env into os.environ so the langsmith SDK
    (which reads the environment directly) picks them up under a plain uvicorn run.
    Real env vars win — we only fill what's unset.

    Tracing is enabled ONLY when an API key is present: turning tracing on without
    a key floods LangSmith 401 errors."""
    if not settings.langsmith_api_key:
        return
    for name, val in (
        ("LANGSMITH_TRACING", settings.langsmith_tracing or "true"),
        ("LANGSMITH_API_KEY", settings.langsmith_api_key),
        ("LANGSMITH_PROJECT", settings.langsmith_project),
    ):
        if val and name not in os.environ:
            os.environ[name] = val


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    apply_langsmith_env(settings)
    app = FastAPI(
        title="Project Lockdown — Detection Core",
        version="0.1.0",
        summary="Stateless classifier that emits the verdict contract (design doc §5).",
    )

    # The background worker calls this cross-origin. Default "*" for local dev;
    # set explicit extension + dashboard origins in production (settings).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )

    service = build_service(settings)
    repository, device_repo = _build_persistence(settings)

    # Adapt the device-token repo into the resolver the authorizer expects:
    # plaintext token -> AuthContext, or None when unknown/revoked.
    device_resolver = None
    if device_repo is not None:

        async def device_resolver(token: str) -> AuthContext | None:
            resolved = await device_repo.resolve(token)
            if resolved is None:
                return None
            return AuthContext(
                user_id=resolved.clerk_user_id, org_id=resolved.clerk_org_id, tier=resolved.tier
            )

    authorize = build_authorizer(
        settings,
        RateLimiter(settings.rate_limit_per_minute, settings.rate_limit_burst),
        device_resolver=device_resolver,
    )
    if repository is not None:
        from lockdown_core.persistence.repository import should_persist

    # Parent-facing token management (Clerk-authed; the dashboard calls this).
    app.include_router(
        build_device_token_router(device_repo, build_clerk_authorizer(settings))
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "version": app.version}

    @app.post("/classify", response_model=Verdict, response_model_exclude_none=False)
    async def classify(
        req: ClassifyRequest,
        background: BackgroundTasks,
        auth: AuthContext = Depends(authorize),
    ) -> Verdict:
        # `auth` identifies the account (rejects anonymous / rate-limited callers).
        # Defensive cap on window size (§4: proportionate capture).
        if len(req.windowed_text) > settings.max_window_turns:
            req = req.model_copy(
                update={"windowed_text": req.windowed_text[-settings.max_window_turns :]}
            )
        verdict = await service.classify(req)

        # Persist lock/log verdicts off the response path (never NO_ACTION). A store
        # outage never blocks the decision — save() swallows its own errors.
        if repository is not None and should_persist(verdict):
            background.add_task(
                repository.save,
                verdict,
                clerk_user_id=auth.user_id,
                clerk_org_id=auth.org_id,
            )

        return verdict

    return app


app = create_app()
