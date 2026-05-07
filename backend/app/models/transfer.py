from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class TransferSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transfer_sessions"

    owner_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    public_token: Mapped[str | None] = mapped_column(String(96), unique=True, index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(160), default="XuanDrop", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)


class TransferItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transfer_items"

    session_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("transfer_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    owner_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    file_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("file_assets.id", ondelete="CASCADE"), index=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="received", index=True, nullable=False)
    saved_to: Mapped[str | None] = mapped_column(String(32), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
