"""FastAPI app — the composition root.

Wires the classifier (real Anthropic SDK, or the deterministic fake when no key),
the notifier (Resend, or the logging stub when no key), and the async pipeline.
Keeps the hot path a thin ``text in → verdict out`` HTTP surface.
"""

from __future__ import annotations

import logging
import os

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from lockdown_core.auth.clerk import AuthContext
from lockdown_core.auth.dependencies import build_authorizer, build_clerk_authorizer
from lockdown_core.auth.device_router import build_device_token_router
from lockdown_core.auth.ratelimit import RateLimiter
from lockdown_core.classify.service import ClassificationService
from lockdown_core.classify.types import Classifier
from lockdown_core.contract.actions import Thresholds, triggers_notification
from lockdown_core.contract.verdict import ClassifyRequest, Stage, Status, Verdict
from lockdown_core.notify.base import Notifier
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
    """``(verdict_repo, device_token_repo, prefs_repo)`` off one Neon engine, or
    ``(None, None, None)``.

    The device-token and preferences repos are built whenever a ``database_url``
    is set (even if verdict persistence is off) — extension auth and notification
    routing need them independent of whether we're storing verdicts. Imported
    lazily HERE (composition root) so sqlalchemy stays off the classifier hot
    path."""
    if not settings.database_url:
        return None, None, None
    from lockdown_core.persistence import (
        DeviceTokenRepository,
        NotificationPreferencesRepository,
        VerdictRepository,
        make_engine,
        make_sessionmaker,
    )

    sessionmaker = make_sessionmaker(make_engine(settings.database_url))
    verdict_repo = VerdictRepository(sessionmaker) if settings.persist_verdicts else None
    return (
        verdict_repo,
        DeviceTokenRepository(sessionmaker),
        NotificationPreferencesRepository(sessionmaker),
    )


def _build_notifier(settings: Settings) -> Notifier:
    if not settings.resend_api_key:
        logger.warning("Using LOG notifier (no RESEND_API_KEY).")
        from lockdown_core.notify.stub import LoggingNotifier

        return LoggingNotifier()
    # Imported lazily HERE (composition root) so httpx stays off the hot path.
    from lockdown_core.notify.resend import ResendNotifier

    return ResendNotifier(
        api_key=settings.resend_api_key, from_email=settings.notify_from_email
    )


def _build_dispatcher(settings: Settings, prefs_repo):
    """Background notification dispatcher: prefs → Clerk email → notifier."""
    from lockdown_core.notify.clerk_email import build_clerk_email_resolver
    from lockdown_core.notify.dispatcher import NotificationDispatcher

    return NotificationDispatcher(
        notifier=_build_notifier(settings),
        prefs=prefs_repo,
        resolve_email=build_clerk_email_resolver(settings.clerk_secret_key),
    )


def build_service(settings: Settings | None = None) -> ClassificationService:
    settings = settings or get_settings()
    return ClassificationService(
        classifier=_build_classifier(settings),
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
    repository, device_repo, prefs_repo = _build_persistence(settings)
    dispatcher = _build_dispatcher(settings, prefs_repo)

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

    # Parent-facing token management + notification prefs (Clerk-authed; the
    # dashboard calls these).
    app.include_router(
        build_device_token_router(device_repo, build_clerk_authorizer(settings))
    )
    from lockdown_core.notify.router import build_notification_settings_router

    app.include_router(
        build_notification_settings_router(prefs_repo, build_clerk_authorizer(settings))
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "version": app.version}

    async def _finalize_tier2(
        req: ClassifyRequest, pending: Verdict, *, clerk_user_id: str, clerk_org_id: str | None
    ) -> None:
        """Background tier-2: verify the PENDING lock, persist the outcome, and
        notify on a confirmed notify-action. The client polls /verdict-status for
        the result (OVERTURNED → unlock; CONFIRMED → lock hardens). Never raises —
        on failure the verdict simply stays PENDING for review."""
        try:
            v2 = await service.verify(pending, req, category=req.category_set[0])
            if v2.stage is not Stage.TIER2:
                return  # tier-2 failed; verify() already logged, lock stays PENDING
            if repository is not None:
                # Persist even OVERTURNED (its action may be NO_ACTION): the tier-2
                # row IS the unlock signal the polling client waits for.
                await repository.save(v2, clerk_user_id=clerk_user_id, clerk_org_id=clerk_org_id)
            if v2.status is Status.CONFIRMED and triggers_notification(v2.recommended_action):
                await dispatcher.dispatch(v2, clerk_user_id=clerk_user_id, clerk_org_id=clerk_org_id)
        except Exception:  # noqa: BLE001 — background finalization must never propagate
            logger.exception("async tier-2 finalization failed for verdict %s", pending.verdict_id)

    @app.get("/verdict-status/{verdict_id}")
    async def verdict_status(
        verdict_id: str, auth: AuthContext = Depends(authorize)
    ) -> dict[str, str]:
        """Post-lock polling surface for the extension (device-token authed).
        Reports the latest persisted stage of one of the caller's own verdicts."""
        if repository is None:
            raise HTTPException(status_code=503, detail="verdict store not configured")
        view = await repository.get_status(verdict_id, clerk_user_id=auth.user_id)
        if view is None:
            raise HTTPException(status_code=404, detail="verdict not found")
        return {
            "verdict_id": view.verdict_id,
            "stage": view.stage,
            "status": view.status,
            "recommended_action": view.recommended_action,
        }

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

        # Notify the parent off the response path, only for a verified verdict
        # (§1: verified before alert — notify actions only exist at tier-2).
        # dispatch() swallows its own errors, mirroring repository.save.
        if verdict.status is Status.CONFIRMED and triggers_notification(
            verdict.recommended_action
        ):
            background.add_task(
                dispatcher.dispatch,
                verdict,
                clerk_user_id=auth.user_id,
                clerk_org_id=auth.org_id,
            )

        # A PENDING tier-1 lock means tier-2 hasn't run (async mode, or the
        # inline pass degraded): finish verification off the response path so
        # the lock lands at tier-1 latency. Runs after the save above, so the
        # TIER1 row exists before the TIER2 row the client polls for.
        if verdict.stage is Stage.TIER1 and verdict.status is Status.PENDING:
            background.add_task(
                _finalize_tier2,
                req,
                verdict,
                clerk_user_id=auth.user_id,
                clerk_org_id=auth.org_id,
            )

        return verdict

    return app


app = create_app()
