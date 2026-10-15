from uuid import UUID

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Note(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A quick note: plain text, with images placed on their own lines as ``[[img:<id>]]``."""

    __tablename__ = "notes"

    owner_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class NoteImage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "note_images"

    note_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), index=True, nullable=False)
    owner_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int | None] = mapped_column(nullable=True)
    height: Mapped[int | None] = mapped_column(nullable=True)
    encrypted_path: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_file_key: Mapped[str] = mapped_column(Text, nullable=False)
    nonce: Mapped[str] = mapped_column(Text, nullable=False)
    auth_tag: Mapped[str] = mapped_column(Text, nullable=False)
