"""shares

Revision ID: 0005_shares
Revises: 0004_receipts_drop
Create Date: 2026-05-07 12:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_shares"
down_revision: str | None = "0004_receipts_drop"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shares",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shared_with_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("public_token", sa.String(length=128), nullable=False),
        sa.Column("permission", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("max_downloads", sa.Integer(), nullable=True),
        sa.Column("download_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shared_with_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shares_expires_at"), "shares", ["expires_at"], unique=False)
    op.create_index(op.f("ix_shares_is_active"), "shares", ["is_active"], unique=False)
    op.create_index(op.f("ix_shares_owner_id"), "shares", ["owner_id"], unique=False)
    op.create_index(op.f("ix_shares_public_token"), "shares", ["public_token"], unique=True)
    op.create_index(op.f("ix_shares_shared_with_user_id"), "shares", ["shared_with_user_id"], unique=False)
    op.create_index(op.f("ix_shares_target_id"), "shares", ["target_id"], unique=False)
    op.create_index(op.f("ix_shares_target_type"), "shares", ["target_type"], unique=False)

    op.create_table(
        "share_access_logs",
        sa.Column("share_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("failure_reason", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["share_id"], ["shares.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_share_access_logs_action"), "share_access_logs", ["action"], unique=False)
    op.create_index(op.f("ix_share_access_logs_actor_user_id"), "share_access_logs", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_share_access_logs_share_id"), "share_access_logs", ["share_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_share_access_logs_share_id"), table_name="share_access_logs")
    op.drop_index(op.f("ix_share_access_logs_actor_user_id"), table_name="share_access_logs")
    op.drop_index(op.f("ix_share_access_logs_action"), table_name="share_access_logs")
    op.drop_table("share_access_logs")
    op.drop_index(op.f("ix_shares_target_type"), table_name="shares")
    op.drop_index(op.f("ix_shares_target_id"), table_name="shares")
    op.drop_index(op.f("ix_shares_shared_with_user_id"), table_name="shares")
    op.drop_index(op.f("ix_shares_public_token"), table_name="shares")
    op.drop_index(op.f("ix_shares_owner_id"), table_name="shares")
    op.drop_index(op.f("ix_shares_is_active"), table_name="shares")
    op.drop_index(op.f("ix_shares_expires_at"), table_name="shares")
    op.drop_table("shares")
