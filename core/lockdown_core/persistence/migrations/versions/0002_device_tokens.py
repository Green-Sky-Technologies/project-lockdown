"""device_tokens: revocable per-account extension credentials

Revision ID: 0002_device_tokens
Revises: 0001_init
Create Date: 2026-08-02

Mirrors lockdown_core/persistence/models.py DeviceToken. Stores only the SHA-256
hash of the token (never the plaintext), keyed to an account and revocable.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_device_tokens"
down_revision: Union[str, None] = "0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "device_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_device_tokens_token_hash"),
    )
    op.create_index("ix_device_tokens_account_id", "device_tokens", ["account_id"])
    op.create_index("ix_device_tokens_token_hash", "device_tokens", ["token_hash"])


def downgrade() -> None:
    op.drop_index("ix_device_tokens_token_hash", table_name="device_tokens")
    op.drop_index("ix_device_tokens_account_id", table_name="device_tokens")
    op.drop_table("device_tokens")
