"""Pydantic model of the verdict contract.

This module MIRRORS ``contract/verdict.schema.json`` and
``contract/classify-request.schema.json`` (the single sources of truth). Keep it
in sync — regenerate/verify via ``contract/codegen/gen_pydantic.py``. Do not add
fields here without adding them to the schema first (design doc §5: "get this
right in one pass or four inconsistent notions of 'how bad is this' leak across
the codebase").
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0.0"


# --------------------------------------------------------------------------- #
# Enums (design doc §5.2)
# --------------------------------------------------------------------------- #
class Stage(str, Enum):
    RECALL_GATE = "RECALL_GATE"
    TIER1 = "TIER1"
    TIER2 = "TIER2"
    HUMAN = "HUMAN"


class Status(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CLEARED = "CLEARED"
    OVERTURNED = "OVERTURNED"


class Category(str, Enum):
    # VIOLENCE_TO_OTHERS is the only live category in v1; the enum is the
    # extension point for validated future categories (design doc §2, §5.1).
    VIOLENCE_TO_OTHERS = "VIOLENCE_TO_OTHERS"


class DirectedAt(str, Enum):
    OTHERS = "OTHERS"
    SELF = "SELF"
    FICTIONAL_OR_ACADEMIC = "FICTIONAL_OR_ACADEMIC"
    AMBIGUOUS = "AMBIGUOUS"


class Severity(str, Enum):
    """How bad if true."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Imminence(str, Enum):
    """How soon."""

    NONE = "NONE"
    SPECULATIVE = "SPECULATIVE"
    DEVELOPING = "DEVELOPING"
    IMMINENT = "IMMINENT"


class RecommendedAction(str, Enum):
    NO_ACTION = "NO_ACTION"
    LOG_ONLY = "LOG_ONLY"
    LOCK = "LOCK"
    LOCK_AND_NOTIFY = "LOCK_AND_NOTIFY"
    LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES = "LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES"


class CaptureSurface(str, Enum):
    CHROMIUM_EXT = "CHROMIUM_EXT"
    FIREFOX_EXT = "FIREFOX_EXT"
    MANAGED_CHROMEOS = "MANAGED_CHROMEOS"
    NATIVE_AGENT = "NATIVE_AGENT"
    NETWORK_PROXY = "NETWORK_PROXY"


class ReviewerOutcome(str, Enum):
    CONFIRM = "CONFIRM"
    OVERTURN = "OVERTURN"
    NEEDS_MORE = "NEEDS_MORE"


# --------------------------------------------------------------------------- #
# Nested objects
# --------------------------------------------------------------------------- #
class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceSpan(_Strict):
    """Offset pointer into the windowed text; never a copy of the text."""

    start: int = Field(ge=0)
    end: int = Field(ge=0)
    turn_index: int | None = Field(default=None, ge=0)


class Context(_Strict):
    window_turn_count: int = Field(ge=0)
    chatbot_host: str = Field(description="Host only, not full URL.")
    capture_surface: CaptureSurface
    monitored_categories: list[Category] = Field(default_factory=list)


class Review(_Strict):
    """Populated on the async/human path only."""

    reviewed_by: str | None = None
    reviewed_at: str | None = None
    reviewer_outcome: ReviewerOutcome | None = None
    notes: str | None = None


class Sampling(_Strict):
    is_holdout: bool = False
    suppression_eligible: bool = False


class Privacy(_Strict):
    deidentified: bool = False
    retain_as_training: bool = False
    raw_text_ref: str | None = None


# --------------------------------------------------------------------------- #
# The verdict object
# --------------------------------------------------------------------------- #
class Verdict(_Strict):
    schema_version: str = SCHEMA_VERSION
    verdict_id: str
    created_at: str

    stage: Stage
    status: Status

    category: Category
    directed_at: DirectedAt

    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    imminence: Imminence

    recommended_action: RecommendedAction

    rationale: str
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)

    context: Context
    review: Review | None = None
    sampling: Sampling = Field(default_factory=Sampling)
    privacy: Privacy = Field(default_factory=Privacy)


# --------------------------------------------------------------------------- #
# Request contract (classify-request.schema.json)
# --------------------------------------------------------------------------- #
class Turn(_Strict):
    role: str = Field(pattern="^(user|assistant)$")
    text: str


class ClientMetadata(_Strict):
    chatbot_host: str
    capture_surface: CaptureSurface
    monitored_categories: list[Category] = Field(default_factory=list)


class ClassifyRequest(_Strict):
    windowed_text: list[Turn] = Field(min_length=1)
    category_set: list[Category] = Field(min_length=1)
    client_metadata: ClientMetadata
    inline_tier2: bool = False
