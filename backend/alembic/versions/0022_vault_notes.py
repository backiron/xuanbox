"""notes can be kept in the vault; vault items remember where they came from

Revision ID: 0022_vault_notes
Revises: 0021_notes
Create Date: 2026-11-19 10:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0022_vault_notes"
down_revision: str | None = "0021_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("notes", sa.Column("in_vault", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("notes", sa.Column("vaulted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_notes_in_vault"), "notes", ["in_vault"])
    op.add_column("documents", sa.Column("restore_info", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "restore_info")
    op.drop_index(op.f("ix_notes_in_vault"), table_name="notes")
    op.drop_column("notes", "vaulted_at")
    op.drop_column("notes", "in_vault")
