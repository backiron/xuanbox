from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Tag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tags"

    owner_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    color: Mapped[str] = mapped_column(String(32), default="#1E3A5F", nullable=False)


class TagLink(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tag_links"

    owner_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    tag_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), index=True, nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    target_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), index=True, nullable=False)
