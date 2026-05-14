"""add inbox items

Revision ID: 0016_inbox_items
Revises: 0015_doc_intel_profiles
Create Date: 2026-05-13 14:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0016_inbox_items"
down_revision: str | None = "0015_doc_intel_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inbox_items",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("suggested_type", sa.String(length=32), nullable=True),
        sa.Column("suggestion_reason", sa.Text(), nullable=True),
        sa.Column("resolved_as", sa.String(length=32), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["file_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_id"),
    )
    op.create_index(op.f("ix_inbox_items_file_id"), "inbox_items", ["file_id"], unique=False)
    op.create_index(op.f("ix_inbox_items_owner_id"), "inbox_items", ["owner_id"], unique=False)
    op.create_index(op.f("ix_inbox_items_status"), "inbox_items", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_inbox_items_status"), table_name="inbox_items")
    op.drop_index(op.f("ix_inbox_items_owner_id"), table_name="inbox_items")
    op.drop_index(op.f("ix_inbox_items_file_id"), table_name="inbox_items")
    op.drop_table("inbox_items")
