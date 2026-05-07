"""ocr worker

Revision ID: 0007_ocr_worker
Revises: 0006_documents
Create Date: 2026-05-07 14:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007_ocr_worker"
down_revision: str | None = "0006_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("receipts", sa.Column("ocr_status", sa.String(length=32), server_default="not_started", nullable=False))
    op.create_index(op.f("ix_receipts_ocr_status"), "receipts", ["ocr_status"], unique=False)
    op.alter_column("receipts", "ocr_status", server_default=None)

    op.create_table(
        "ocr_tasks",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("parsed_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["file_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ocr_tasks_file_id"), "ocr_tasks", ["file_id"], unique=False)
    op.create_index(op.f("ix_ocr_tasks_owner_id"), "ocr_tasks", ["owner_id"], unique=False)
    op.create_index(op.f("ix_ocr_tasks_receipt_id"), "ocr_tasks", ["receipt_id"], unique=False)
    op.create_index(op.f("ix_ocr_tasks_status"), "ocr_tasks", ["status"], unique=False)

    op.create_table(
        "worker_tasks",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_worker_tasks_owner_id"), "worker_tasks", ["owner_id"], unique=False)
    op.create_index(op.f("ix_worker_tasks_status"), "worker_tasks", ["status"], unique=False)
    op.create_index(op.f("ix_worker_tasks_target_id"), "worker_tasks", ["target_id"], unique=False)
    op.create_index(op.f("ix_worker_tasks_target_type"), "worker_tasks", ["target_type"], unique=False)
    op.create_index(op.f("ix_worker_tasks_task_type"), "worker_tasks", ["task_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_worker_tasks_task_type"), table_name="worker_tasks")
    op.drop_index(op.f("ix_worker_tasks_target_type"), table_name="worker_tasks")
    op.drop_index(op.f("ix_worker_tasks_target_id"), table_name="worker_tasks")
    op.drop_index(op.f("ix_worker_tasks_status"), table_name="worker_tasks")
    op.drop_index(op.f("ix_worker_tasks_owner_id"), table_name="worker_tasks")
    op.drop_table("worker_tasks")
    op.drop_index(op.f("ix_ocr_tasks_status"), table_name="ocr_tasks")
    op.drop_index(op.f("ix_ocr_tasks_receipt_id"), table_name="ocr_tasks")
    op.drop_index(op.f("ix_ocr_tasks_owner_id"), table_name="ocr_tasks")
    op.drop_index(op.f("ix_ocr_tasks_file_id"), table_name="ocr_tasks")
    op.drop_table("ocr_tasks")
    op.drop_index(op.f("ix_receipts_ocr_status"), table_name="receipts")
    op.drop_column("receipts", "ocr_status")
