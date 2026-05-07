from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class FileAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "file_assets"

    owner_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    folder_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    file_ext: Mapped[str | None] = mapped_column(String(32), nullable=True)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    encrypted_path: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_file_key: Mapped[str] = mapped_column(Text, nullable=False)
    encryption_method: Mapped[str] = mapped_column(String(64), default="AES-256-GCM", nullable=False)
    nonce: Mapped[str] = mapped_column(Text, nullable=False)
    auth_tag: Mapped[str] = mapped_column(Text, nullable=False)
    key_version: Mapped[int] = mapped_column(default=1, nullable=False)
    file_category: Mapped[str] = mapped_column(String(64), default="other", index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="manual_upload", nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="files")
