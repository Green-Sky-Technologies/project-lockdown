"""The classifier's structured output — the model-supplied subset of a Verdict.

This is exactly the schema an Anthropic structured-outputs call is constrained
to (a projection of the verdict contract). The model supplies the *judgment*
axes (design doc §5.1: severity / confidence / imminence are separate axes, and
``directed_at`` separates a threat from a book report). It NEVER supplies
``recommended_action`` — that is derived server-side in ``contract.actions``.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from lockdown_core.contract.verdict import (
    Category,
    DirectedAt,
    EvidenceSpan,
    Imminence,
    Severity,
    Stage,
    Turn,
)


class ClassifierJudgment(BaseModel):
    """The constrained structured output of a tier-1 or tier-2 classifier call."""

    model_config = ConfigDict(extra="forbid")

    directed_at: DirectedAt = Field(
        description="Who the potential harm is aimed at. The field that separates "
        "a threat from an academic/fictional discussion."
    )
    severity: Severity = Field(description="How bad if true.")
    confidence: float = Field(ge=0.0, le=1.0, description="How sure you are.")
    imminence: Imminence = Field(description="How soon.")
    rationale: str = Field(description="One or two sentences, for a human reviewer.")
    evidence_spans: list[EvidenceSpan] = Field(
        default_factory=list,
        description="Character offsets into the relevant turn(s) supporting the judgment.",
    )


class Classifier(Protocol):
    """Both tiers implement this. Stateless: text in → judgment out."""

    async def judge(
        self,
        *,
        tier: Stage,
        window: list[Turn],
        category: Category,
    ) -> ClassifierJudgment: ...
