from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class DropContact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "drop_contacts"
    __table_args__ = (UniqueConstraint("requester_id", "addressee_id", name="uq_drop_contacts_pair"),)

    requester_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    addressee_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True, nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DropThread(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "drop_threads"

    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # "self:<user_id>" or "direct:<smaller_user_id>:<larger_user_id>"
    thread_key: Mapped[str] = mapped_column(String(96), unique=True, index=True, nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)


class DropThreadMember(Base):
    __tablename__ = "drop_thread_members"

    thread_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("drop_threads.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DropMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "drop_messages"

    thread_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("drop_threads.id", ondelete="CASCADE"), index=True, nullable=False)
    sender_user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    sender_device_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    # Shown instead of a device name for messages that did not come from a signed-in device (QR uploads).
    sender_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    target_device_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    encrypted_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_file_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    nonce: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_tag: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumb_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumb_file_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumb_nonce: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumb_auth_tag: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_width: Mapped[int | None] = mapped_column(nullable=True)
    image_height: Mapped[int | None] = mapped_column(nullable=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)


class DropMessageSave(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "drop_message_saves"
    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_drop_message_saves_message_user"),)

    message_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("drop_messages.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    destination: Mapped[str] = mapped_column(String(32), nullable=False)
    file_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("file_assets.id", ondelete="SET NULL"), nullable=True)
