"""admin backups

Revision ID: 0008_admin_backups
Revises: 0007_ocr_worker
Create Date: 2026-05-07 15:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008_admin_backups"
down_revision: str | None = "0007_ocr_worker"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "backup_tasks",
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("backup_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("backup_path", sa.Text(), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("manifest_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_backup_tasks_backup_type"), "backup_tasks", ["backup_type"], unique=False)
    op.create_index(op.f("ix_backup_tasks_requested_by_user_id"), "backup_tasks", ["requested_by_user_id"], unique=False)
    op.create_index(op.f("ix_backup_tasks_status"), "backup_tasks", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_backup_tasks_status"), table_name="backup_tasks")
    op.drop_index(op.f("ix_backup_tasks_requested_by_user_id"), table_name="backup_tasks")
    op.drop_index(op.f("ix_backup_tasks_backup_type"), table_name="backup_tasks")
    op.drop_table("backup_tasks")
