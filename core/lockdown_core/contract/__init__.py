"""The verdict contract (design doc §5) and its derived action mapping (§5.3).

``verdict.py`` mirrors ``contract/verdict.schema.json`` (the single source of
truth) — regenerate/verify via ``contract/codegen/gen_pydantic.py``. ``actions.py``
is the ONE place the verdict→recommended_action thresholds live.
"""

from lockdown_core.contract.verdict import (
    Category,
    ClassifyRequest,
    ClientMetadata,
    Context,
    DirectedAt,
    EvidenceSpan,
    Imminence,
    Privacy,
    RecommendedAction,
    Review,
    ReviewerOutcome,
    Sampling,
    Severity,
    Stage,
    Status,
    Turn,
    Verdict,
)

__all__ = [
    "Category",
    "ClassifyRequest",
    "ClientMetadata",
    "Context",
    "DirectedAt",
    "EvidenceSpan",
    "Imminence",
    "Privacy",
    "RecommendedAction",
    "Review",
    "ReviewerOutcome",
    "Sampling",
    "Severity",
    "Stage",
    "Status",
    "Turn",
    "Verdict",
]
