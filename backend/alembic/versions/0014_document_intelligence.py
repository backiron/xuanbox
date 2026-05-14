"""document intelligence

Revision ID: 0014_document_intelligence
Revises: 0013_messages
Create Date: 2026-05-13 00:20:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0014_document_intelligence"
down_revision: str | None = "0013_messages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_intelligence_tasks",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("detected_type", sa.String(length=64), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("parsed_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["file_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_intelligence_tasks_detected_type"), "document_intelligence_tasks", ["detected_type"], unique=False)
    op.create_index(op.f("ix_document_intelligence_tasks_file_id"), "document_intelligence_tasks", ["file_id"], unique=False)
    op.create_index(op.f("ix_document_intelligence_tasks_owner_id"), "document_intelligence_tasks", ["owner_id"], unique=False)
    op.create_index(op.f("ix_document_intelligence_tasks_source_type"), "document_intelligence_tasks", ["source_type"], unique=False)
    op.create_index(op.f("ix_document_intelligence_tasks_status"), "document_intelligence_tasks", ["status"], unique=False)

    op.create_table(
        "document_profiles",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("document_type", sa.String(length=64), nullable=False),
        sa.Column("issuer", sa.String(length=255), nullable=True),
        sa.Column("primary_date", sa.String(length=32), nullable=True),
        sa.Column("amount", sa.String(length=64), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("warranty_until", sa.String(length=32), nullable=True),
        sa.Column("serial_number", sa.String(length=120), nullable=True),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["file_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["document_intelligence_tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_id"),
    )
    op.create_index(op.f("ix_document_profiles_document_type"), "document_profiles", ["document_type"], unique=False)
    op.create_index(op.f("ix_document_profiles_owner_id"), "document_profiles", ["owner_id"], unique=False)

    op.create_table(
        "document_text_chunks",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["file_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["document_intelligence_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_text_chunks_file_id"), "document_text_chunks", ["file_id"], unique=False)
    op.create_index(op.f("ix_document_text_chunks_owner_id"), "document_text_chunks", ["owner_id"], unique=False)
    op.create_index(op.f("ix_document_text_chunks_task_id"), "document_text_chunks", ["task_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_document_text_chunks_task_id"), table_name="document_text_chunks")
    op.drop_index(op.f("ix_document_text_chunks_owner_id"), table_name="document_text_chunks")
    op.drop_index(op.f("ix_document_text_chunks_file_id"), table_name="document_text_chunks")
    op.drop_table("document_text_chunks")
    op.drop_index(op.f("ix_document_profiles_owner_id"), table_name="document_profiles")
    op.drop_index(op.f("ix_document_profiles_document_type"), table_name="document_profiles")
    op.drop_table("document_profiles")
    op.drop_index(op.f("ix_document_intelligence_tasks_status"), table_name="document_intelligence_tasks")
    op.drop_index(op.f("ix_document_intelligence_tasks_source_type"), table_name="document_intelligence_tasks")
    op.drop_index(op.f("ix_document_intelligence_tasks_owner_id"), table_name="document_intelligence_tasks")
    op.drop_index(op.f("ix_document_intelligence_tasks_file_id"), table_name="document_intelligence_tasks")
    op.drop_index(op.f("ix_document_intelligence_tasks_detected_type"), table_name="document_intelligence_tasks")
    op.drop_table("document_intelligence_tasks")
