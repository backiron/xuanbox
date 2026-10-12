"""add XuanDrop chat threads, contacts and device client keys

Revision ID: 0018_drop_chat
Revises: 0017_system_settings
Create Date: 2026-10-11 12:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0018_drop_chat"
down_revision: str | None = "0017_system_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("devices", sa.Column("client_key_hash", sa.String(length=128), nullable=True))
    op.create_index(op.f("ix_devices_client_key_hash"), "devices", ["client_key_hash"], unique=False)

    op.create_table(
        "drop_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("addressee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requester_id", "addressee_id", name="uq_drop_contacts_pair"),
    )
    op.create_index(op.f("ix_drop_contacts_requester_id"), "drop_contacts", ["requester_id"])
    op.create_index(op.f("ix_drop_contacts_addressee_id"), "drop_contacts", ["addressee_id"])
    op.create_index(op.f("ix_drop_contacts_status"), "drop_contacts", ["status"])

    op.create_table(
        "drop_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("thread_key", sa.String(length=96), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_drop_threads_thread_key"), "drop_threads", ["thread_key"], unique=True)
    op.create_index(op.f("ix_drop_threads_last_message_at"), "drop_threads", ["last_message_at"])

    op.create_table(
        "drop_thread_members",
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drop_threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("thread_id", "user_id"),
    )
    op.create_index(op.f("ix_drop_thread_members_user_id"), "drop_thread_members", ["user_id"])

    op.create_table(
        "drop_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drop_threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sender_label", sa.String(length=160), nullable=True),
        sa.Column("target_device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("mime_type", sa.String(length=160), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("encrypted_path", sa.Text(), nullable=True),
        sa.Column("encrypted_file_key", sa.Text(), nullable=True),
        sa.Column("nonce", sa.Text(), nullable=True),
        sa.Column("auth_tag", sa.Text(), nullable=True),
        sa.Column("thumb_path", sa.Text(), nullable=True),
        sa.Column("thumb_file_key", sa.Text(), nullable=True),
        sa.Column("thumb_nonce", sa.Text(), nullable=True),
        sa.Column("thumb_auth_tag", sa.Text(), nullable=True),
        sa.Column("image_width", sa.Integer(), nullable=True),
        sa.Column("image_height", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_drop_messages_thread_id"), "drop_messages", ["thread_id"])
    op.create_index(op.f("ix_drop_messages_sender_user_id"), "drop_messages", ["sender_user_id"])
    op.create_index(op.f("ix_drop_messages_expires_at"), "drop_messages", ["expires_at"])
    op.create_index("ix_drop_messages_thread_created", "drop_messages", ["thread_id", "created_at"])

    op.create_table(
        "drop_message_saves",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drop_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("destination", sa.String(length=32), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("file_assets.id", ondelete="SET NULL"), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "user_id", name="uq_drop_message_saves_message_user"),
    )
    op.create_index(op.f("ix_drop_message_saves_message_id"), "drop_message_saves", ["message_id"])
    op.create_index(op.f("ix_drop_message_saves_user_id"), "drop_message_saves", ["user_id"])


def downgrade() -> None:
    op.drop_table("drop_message_saves")
    op.drop_index("ix_drop_messages_thread_created", table_name="drop_messages")
    op.drop_table("drop_messages")
    op.drop_table("drop_thread_members")
    op.drop_table("drop_threads")
    op.drop_table("drop_contacts")
    op.drop_index(op.f("ix_devices_client_key_hash"), table_name="devices")
    op.drop_column("devices", "client_key_hash")
