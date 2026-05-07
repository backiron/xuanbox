"""initial security skeleton

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-07 00:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("avatar_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("storage_limit_bytes", sa.BigInteger(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "devices",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_name", sa.String(length=120), nullable=False),
        sa.Column("device_type", sa.String(length=64), nullable=False),
        sa.Column("os_name", sa.String(length=120), nullable=True),
        sa.Column("browser_name", sa.String(length=120), nullable=True),
        sa.Column("last_ip", sa.String(length=64), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_trusted", sa.Boolean(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_devices_owner_id"), "devices", ["owner_id"], unique=False)

    op.create_table(
        "file_assets",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=160), nullable=True),
        sa.Column("file_ext", sa.String(length=32), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("encrypted_path", sa.Text(), nullable=False),
        sa.Column("encrypted_file_key", sa.Text(), nullable=False),
        sa.Column("encryption_method", sa.String(length=64), nullable=False),
        sa.Column("nonce", sa.Text(), nullable=False),
        sa.Column("auth_tag", sa.Text(), nullable=False),
        sa.Column("key_version", sa.Integer(), nullable=False),
        sa.Column("file_category", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("is_favorite", sa.Boolean(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_file_assets_file_category"), "file_assets", ["file_category"], unique=False)
    op.create_index(op.f("ix_file_assets_owner_id"), "file_assets", ["owner_id"], unique=False)
    op.create_index(op.f("ix_file_assets_sha256_hash"), "file_assets", ["sha256_hash"], unique=False)

    op.create_table(
        "invites",
        sa.Column("invite_code", sa.String(length=96), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_to_assign", sa.String(length=32), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invites_invite_code"), "invites", ["invite_code"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_invites_invite_code"), table_name="invites")
    op.drop_table("invites")
    op.drop_index(op.f("ix_file_assets_sha256_hash"), table_name="file_assets")
    op.drop_index(op.f("ix_file_assets_owner_id"), table_name="file_assets")
    op.drop_index(op.f("ix_file_assets_file_category"), table_name="file_assets")
    op.drop_table("file_assets")
    op.drop_index(op.f("ix_devices_owner_id"), table_name="devices")
    op.drop_table("devices")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
