"""chunked XuanDrop uploads

Revision ID: 0019_drop_chunked_uploads
Revises: 0018_drop_chat
Create Date: 2026-10-11 20:30:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0019_drop_chunked_uploads"
down_revision: str | None = "0018_drop_chat"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("drop_messages", sa.Column("encryption_format", sa.String(length=16), nullable=False, server_default="single"))
    op.create_table(
        "drop_uploads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drop_threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=160), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=False),
        sa.Column("next_index", sa.Integer(), nullable=False),
        sa.Column("received_bytes", sa.BigInteger(), nullable=False),
        sa.Column("encrypted_path", sa.Text(), nullable=False),
        sa.Column("encrypted_file_key", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_drop_uploads_thread_id"), "drop_uploads", ["thread_id"])
    op.create_index(op.f("ix_drop_uploads_user_id"), "drop_uploads", ["user_id"])
    op.create_index(op.f("ix_drop_uploads_expires_at"), "drop_uploads", ["expires_at"])


def downgrade() -> None:
    op.drop_table("drop_uploads")
    op.drop_column("drop_messages", "encryption_format")
