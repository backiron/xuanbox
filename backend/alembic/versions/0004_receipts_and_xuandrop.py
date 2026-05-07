"""receipts and xuandrop

Revision ID: 0004_receipts_drop
Revises: 0003_files_photos
Create Date: 2026-05-07 01:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_receipts_drop"
down_revision: str | None = "0003_files_photos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "receipts",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("merchant", sa.String(length=160), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("warranty_until", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["file_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_receipts_category"), "receipts", ["category"], unique=False)
    op.create_index(op.f("ix_receipts_file_id"), "receipts", ["file_id"], unique=False)
    op.create_index(op.f("ix_receipts_merchant"), "receipts", ["merchant"], unique=False)
    op.create_index(op.f("ix_receipts_owner_id"), "receipts", ["owner_id"], unique=False)
    op.create_index(op.f("ix_receipts_purchase_date"), "receipts", ["purchase_date"], unique=False)
    op.create_index(op.f("ix_receipts_warranty_until"), "receipts", ["warranty_until"], unique=False)

    op.create_table(
        "transfer_sessions",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transfer_sessions_expires_at"), "transfer_sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_transfer_sessions_owner_id"), "transfer_sessions", ["owner_id"], unique=False)
    op.create_index(op.f("ix_transfer_sessions_status"), "transfer_sessions", ["status"], unique=False)
    op.create_index(op.f("ix_transfer_sessions_token_hash"), "transfer_sessions", ["token_hash"], unique=True)

    op.create_table(
        "transfer_items",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=160), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("saved_to", sa.String(length=32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["file_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["transfer_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transfer_items_file_id"), "transfer_items", ["file_id"], unique=False)
    op.create_index(op.f("ix_transfer_items_owner_id"), "transfer_items", ["owner_id"], unique=False)
    op.create_index(op.f("ix_transfer_items_session_id"), "transfer_items", ["session_id"], unique=False)
    op.create_index(op.f("ix_transfer_items_status"), "transfer_items", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_transfer_items_status"), table_name="transfer_items")
    op.drop_index(op.f("ix_transfer_items_session_id"), table_name="transfer_items")
    op.drop_index(op.f("ix_transfer_items_owner_id"), table_name="transfer_items")
    op.drop_index(op.f("ix_transfer_items_file_id"), table_name="transfer_items")
    op.drop_table("transfer_items")
    op.drop_index(op.f("ix_transfer_sessions_token_hash"), table_name="transfer_sessions")
    op.drop_index(op.f("ix_transfer_sessions_status"), table_name="transfer_sessions")
    op.drop_index(op.f("ix_transfer_sessions_owner_id"), table_name="transfer_sessions")
    op.drop_index(op.f("ix_transfer_sessions_expires_at"), table_name="transfer_sessions")
    op.drop_table("transfer_sessions")
    op.drop_index(op.f("ix_receipts_warranty_until"), table_name="receipts")
    op.drop_index(op.f("ix_receipts_purchase_date"), table_name="receipts")
    op.drop_index(op.f("ix_receipts_owner_id"), table_name="receipts")
    op.drop_index(op.f("ix_receipts_merchant"), table_name="receipts")
    op.drop_index(op.f("ix_receipts_file_id"), table_name="receipts")
    op.drop_index(op.f("ix_receipts_category"), table_name="receipts")
    op.drop_table("receipts")
