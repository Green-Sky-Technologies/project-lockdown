"""Guard the hand-maintained Pydantic mirror against the JSON Schema source.

Rather than text-diffing generator output, we assert *behavioural* parity:

1. Every enum in the schema has exactly the same members in the Pydantic model.
2. A fully-populated ``Verdict`` serialized to JSON validates against
   ``contract/verdict.schema.json``.

Either check fails the moment the schema and the mirror drift.
"""

import json
from pathlib import Path

import jsonschema
import pytest

from lockdown_core.contract.verdict import (
    CaptureSurface,
    Category,
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
    Verdict,
)

REPO = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO / "contract" / "verdict.schema.json").read_text())


ENUM_PAIRS = [
    ("Stage", Stage),
    ("Status", Status),
    ("Category", Category),
    ("DirectedAt", DirectedAt),
    ("Severity", Severity),
    ("Imminence", Imminence),
    ("RecommendedAction", RecommendedAction),
    ("CaptureSurface", CaptureSurface),
    ("ReviewerOutcome", ReviewerOutcome),
]


@pytest.mark.parametrize("def_name,enum_cls", ENUM_PAIRS)
def test_enum_members_match_schema(def_name, enum_cls):
    schema_values = set(SCHEMA["$defs"][def_name]["enum"])
    model_values = {m.value for m in enum_cls}
    assert model_values == schema_values, f"{def_name} drifted from the schema"


def test_populated_verdict_validates_against_schema():
    verdict = Verdict(
        verdict_id="11111111-1111-4111-8111-111111111111",
        created_at="2026-07-01T12:00:00Z",
        stage=Stage.TIER2,
        status=Status.CONFIRMED,
        category=Category.VIOLENCE_TO_OTHERS,
        directed_at=DirectedAt.OTHERS,
        severity=Severity.HIGH,
        confidence=0.91,
        imminence=Imminence.DEVELOPING,
        recommended_action=RecommendedAction.LOCK_AND_NOTIFY,
        rationale="Repeated targeting of a named peer with a stated plan.",
        evidence_spans=[EvidenceSpan(start=10, end=42, turn_index=3)],
        context=Context(
            window_turn_count=6,
            chatbot_host="chatgpt.com",
            capture_surface=CaptureSurface.CHROMIUM_EXT,
            monitored_categories=[Category.VIOLENCE_TO_OTHERS],
        ),
        review=Review(
            reviewed_by="reviewer-7",
            reviewed_at="2026-07-01T12:05:00Z",
            reviewer_outcome=ReviewerOutcome.CONFIRM,
            notes=None,
        ),
        sampling=Sampling(is_holdout=True, suppression_eligible=False),
        privacy=Privacy(deidentified=True, retain_as_training=False, raw_text_ref=None),
    )
    payload = json.loads(verdict.model_dump_json())
    jsonschema.validate(payload, SCHEMA)


def test_minimal_verdict_validates_against_schema():
    """review is nullable; defaults must still satisfy the schema."""
    verdict = Verdict(
        verdict_id="22222222-2222-4222-8222-222222222222",
        created_at="2026-07-01T12:00:00Z",
        stage=Stage.TIER1,
        status=Status.PENDING,
        category=Category.VIOLENCE_TO_OTHERS,
        directed_at=DirectedAt.AMBIGUOUS,
        severity=Severity.MODERATE,
        confidence=0.4,
        imminence=Imminence.SPECULATIVE,
        recommended_action=RecommendedAction.LOCK,
        rationale="Ambiguous; locked pending review.",
        context=Context(
            window_turn_count=2,
            chatbot_host="claude.ai",
            capture_surface=CaptureSurface.CHROMIUM_EXT,
            monitored_categories=[Category.VIOLENCE_TO_OTHERS],
        ),
    )
    payload = json.loads(verdict.model_dump_json())
    jsonschema.validate(payload, SCHEMA)
