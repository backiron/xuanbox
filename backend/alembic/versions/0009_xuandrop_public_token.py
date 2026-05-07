"""xuandrop public token

Revision ID: 0009_xuandrop_public_token
Revises: 0008_admin_backups
Create Date: 2026-05-07 17:10:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0009_xuandrop_public_token"
down_revision: str | None = "0008_admin_backups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("transfer_sessions", sa.Column("public_token", sa.String(length=96), nullable=True))
    op.create_index(op.f("ix_transfer_sessions_public_token"), "transfer_sessions", ["public_token"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_transfer_sessions_public_token"), table_name="transfer_sessions")
    op.drop_column("transfer_sessions", "public_token")
