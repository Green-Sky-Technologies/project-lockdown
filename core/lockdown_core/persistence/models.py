"""ORM models — privacy-minimal (design doc §5.2 / §8).

Cross-dialect column types (``Uuid``, ``JSON``) so the same models map onto Neon
(Postgres) in production and async SQLite in tests. No raw-text columns exist —
only offset spans and a short rationale; governance toggle columns
(``retain_as_training``, ``retention_expires_at``, ``deidentified``) are present
but policy sets their values, not code (§8/§11).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    clerk_user_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    clerk_org_id: Mapped[str | None] = mapped_column(String, nullable=True)  # school tier
    tier: Mapped[str] = mapped_column(String, nullable=False, default="family")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class VerdictRecord(Base):
    __tablename__ = "verdict_records"
    __table_args__ = (
        # tier-1 (PENDING) and tier-2 (CONFIRMED/OVERTURNED) rows coexist; upsert
        # per (verdict_id, stage) preserves the stage audit trail.
        UniqueConstraint("verdict_id", "stage", name="uq_verdict_stage"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id"), nullable=False, index=True
    )
    clerk_org_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    verdict_id: Mapped[str] = mapped_column(String, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # --- contract render fields (no raw text) ---
    category: Mapped[str] = mapped_column(String, nullable=False)
    directed_at: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    imminence: Mapped[str] = mapped_column(String, nullable=False)
    stage: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    recommended_action: Mapped[str] = mapped_column(String, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_spans: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    chatbot_host: Mapped[str] = mapped_column(String, nullable=False)
    capture_surface: Mapped[str] = mapped_column(String, nullable=False)

    # --- governance / §8 §11 (columns exist; policy sets the values) ---
    deidentified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retain_as_training: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_text_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    retention_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
