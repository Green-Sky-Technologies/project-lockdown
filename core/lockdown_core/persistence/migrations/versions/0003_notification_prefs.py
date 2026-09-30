"""notification_prefs: per-account notification channel choice

Revision ID: 0003_notification_prefs
Revises: 0002_device_tokens
Create Date: 2026-08-26

Mirrors lockdown_core/persistence/models.py Account.notify_channel. Stores only
the channel choice ("dashboard_only" | "email" | later "sms") — never the
address/number, which is resolved from Clerk at send time.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_notification_prefs"
down_revision: Union[str, None] = "0002_device_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column(
            "notify_channel", sa.String(), nullable=False, server_default="dashboard_only"
        ),
    )


def downgrade() -> None:
    op.drop_column("accounts", "notify_channel")
