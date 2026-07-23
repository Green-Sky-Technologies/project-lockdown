"""initial schema: accounts + verdict_records

Revision ID: 0001_init
Revises:
Create Date: 2026-07-21

Mirrors lockdown_core/persistence/models.py. Privacy-minimal (design doc §8):
no raw-text columns; governance toggle columns present with safe defaults.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clerk_user_id", sa.String(), nullable=False),
        sa.Column("clerk_org_id", sa.String(), nullable=True),
        sa.Column("tier", sa.String(), nullable=False, server_default="family"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("clerk_user_id", name="uq_accounts_clerk_user_id"),
    )
    op.create_index("ix_accounts_clerk_user_id", "accounts", ["clerk_user_id"])

    op.create_table(
        "verdict_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("clerk_org_id", sa.String(), nullable=True),
        sa.Column("verdict_id", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("directed_at", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("imminence", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("recommended_action", sa.String(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_spans", sa.JSON(), nullable=False),
        sa.Column("chatbot_host", sa.String(), nullable=False),
        sa.Column("capture_surface", sa.String(), nullable=False),
        sa.Column("deidentified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("retain_as_training", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("raw_text_ref", sa.String(), nullable=True),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("verdict_id", "stage", name="uq_verdict_stage"),
    )
    op.create_index("ix_verdict_records_account_id", "verdict_records", ["account_id"])
    op.create_index("ix_verdict_records_clerk_org_id", "verdict_records", ["clerk_org_id"])


def downgrade() -> None:
    op.drop_index("ix_verdict_records_clerk_org_id", table_name="verdict_records")
    op.drop_index("ix_verdict_records_account_id", table_name="verdict_records")
    op.drop_table("verdict_records")
    op.drop_index("ix_accounts_clerk_user_id", table_name="accounts")
    op.drop_table("accounts")
