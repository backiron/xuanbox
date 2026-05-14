"""share archives

Revision ID: 0011_share_archives
Revises: 0010_important_docs_pin
Create Date: 2026-05-12 22:10:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0011_share_archives"
down_revision: str | None = "0010_important_docs_pin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("shares", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_shares_archived_at"), "shares", ["archived_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_shares_archived_at"), table_name="shares")
    op.drop_column("shares", "archived_at")
