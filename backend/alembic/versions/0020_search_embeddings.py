"""search embeddings for meaning-based search

Revision ID: 0020_search_embeddings
Revises: 0019_drop_chunked_uploads
Create Date: 2026-10-11 21:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0020_search_embeddings"
down_revision: str | None = "0019_drop_chunked_uploads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("file_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("vector", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_type", "source_id", "chunk_index", name="uq_search_embeddings_source_chunk"),
    )
    op.create_index(op.f("ix_search_embeddings_owner_id"), "search_embeddings", ["owner_id"])
    op.create_index(op.f("ix_search_embeddings_file_id"), "search_embeddings", ["file_id"])
    op.create_index(op.f("ix_search_embeddings_source_id"), "search_embeddings", ["source_id"])


def downgrade() -> None:
    op.drop_table("search_embeddings")
