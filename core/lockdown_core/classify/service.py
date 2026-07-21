"""Classification orchestration (design doc §4.3).

Flow (all off the child's critical path — we observe the DOM, we are not in the
request path, §4.1):

    recall gate (client-side) ──▶ /classify
        tier-1 (cheap/recall)
            └─ not concerning ─────────────▶ CLEARED verdict, no lock
            └─ concerning ── LOCK now ──▶ PENDING verdict (lock overlay)
                    tier-2 (precise/verifying)
                        └─ confirms ───────▶ CONFIRMED verdict ─▶ notify + pipeline
                        └─ clears ─────────▶ OVERTURNED verdict (lock lifted)

``inline_tier2`` runs tier-2 in the same request (skeleton convenience / school
inline mode); otherwise tier-2 + pipeline run asynchronously (M4 wires the
background task) and the caller gets the PENDING verdict immediately.

The verdict is assembled here; ``recommended_action`` is derived — never model-
chosen — and is the single computed decision every surface renders from.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from lockdown_core.classify.types import Classifier, ClassifierJudgment
from lockdown_core.contract.actions import (
    Thresholds,
    crosses_lock_threshold,
    derive_action,
    triggers_notification,
)
from lockdown_core.contract.verdict import (
    Category,
    ClassifyRequest,
    Context,
    Stage,
    Status,
    Verdict,
)
from lockdown_core.notify.base import Notifier
from lockdown_core.pipeline.base import PipelineRunner


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ClassificationService:
    def __init__(
        self,
        *,
        classifier: Classifier,
        notifier: Notifier,
        pipeline: PipelineRunner,
        thresholds: Thresholds,
        default_recipient: str = "unconfigured-adult",
    ) -> None:
        self._classifier = classifier
        self._notifier = notifier
        self._pipeline = pipeline
        self._thresholds = thresholds
        self._default_recipient = default_recipient

    # ---- verdict assembly ------------------------------------------------- #
    def _assemble(
        self,
        judgment: ClassifierJudgment,
        req: ClassifyRequest,
        *,
        stage: Stage,
        status: Status,
        verdict_id: str,
        category: Category,
    ) -> Verdict:
        action = derive_action(
            category=category,
            directed_at=judgment.directed_at,
            imminence=judgment.imminence,
            confidence=judgment.confidence,
            stage=stage,
            thresholds=self._thresholds,
        )
        return Verdict(
            verdict_id=verdict_id,
            created_at=_now_iso(),
            stage=stage,
            status=status,
            category=category,
            directed_at=judgment.directed_at,
            severity=judgment.severity,
            confidence=judgment.confidence,
            imminence=judgment.imminence,
            recommended_action=action,
            rationale=judgment.rationale,
            evidence_spans=judgment.evidence_spans,
            context=Context(
                window_turn_count=len(req.windowed_text),
                chatbot_host=req.client_metadata.chatbot_host,
                capture_surface=req.client_metadata.capture_surface,
                monitored_categories=req.client_metadata.monitored_categories,
            ),
        )

    # ---- entry point ------------------------------------------------------ #
    async def classify(self, req: ClassifyRequest) -> Verdict:
        category = req.category_set[0]  # v1 is single-category
        verdict_id = str(uuid.uuid4())

        # Tier-1: cheap/recall.
        j1 = await self._classifier.judge(
            tier=Stage.TIER1, window=req.windowed_text, category=category
        )
        v1 = self._assemble(
            j1, req, stage=Stage.TIER1, status=Status.PENDING, verdict_id=verdict_id, category=category
        )

        # Not concerning enough to lock: clear it on the cheap path, no tier-2.
        if not crosses_lock_threshold(v1.recommended_action):
            return v1.model_copy(update={"status": Status.CLEARED})

        # Concerning: locked pending review (§2 — a false lock is recoverable).
        if not req.inline_tier2:
            # M4 schedules tier-2 + pipeline as a background task; the client
            # locks now on this PENDING verdict.
            return v1

        return await self._verify(v1, req, category=category)

    async def _verify(self, pending: Verdict, req: ClassifyRequest, *, category: Category) -> Verdict:
        """Tier-2 verifying pass — the CONFIRMED verdict that gates notification."""
        j2 = await self._classifier.judge(
            tier=Stage.TIER2, window=req.windowed_text, category=category
        )
        confirmed = crosses_lock_threshold(
            derive_action(
                category=category,
                directed_at=j2.directed_at,
                imminence=j2.imminence,
                confidence=j2.confidence,
                stage=Stage.TIER2,
                thresholds=self._thresholds,
            )
        )
        v2 = self._assemble(
            j2,
            req,
            stage=Stage.TIER2,
            status=Status.CONFIRMED if confirmed else Status.OVERTURNED,
            verdict_id=pending.verdict_id,  # stable id across pending→confirmed
            category=category,
        )

        if v2.status is Status.CONFIRMED:
            if triggers_notification(v2.recommended_action):
                await self._notifier.send(v2, recipient=self._default_recipient)
            await self._pipeline.run(v2)

        return v2
