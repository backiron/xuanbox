from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Album(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "albums"

    owner_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_file_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("file_assets.id", ondelete="SET NULL"), nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), default="private", nullable=False)


class AlbumPhoto(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "album_photos"

    album_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("albums.id", ondelete="CASCADE"), index=True, nullable=False)
    photo_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("photo_assets.id", ondelete="CASCADE"), index=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
