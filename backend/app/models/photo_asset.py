from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class PhotoAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "photo_assets"

    owner_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    file_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("file_assets.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    camera_model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    orientation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exif_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    location_lat_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_lng_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    thumbnail_file_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("file_assets.id", ondelete="SET NULL"), nullable=True)
    preview_file_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("file_assets.id", ondelete="SET NULL"), nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
