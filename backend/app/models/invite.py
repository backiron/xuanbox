from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import USER_ROLE_USER
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Invite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "invites"

    invite_code: Mapped[str] = mapped_column(String(96), unique=True, index=True, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_to_assign: Mapped[str] = mapped_column(String(32), default=USER_ROLE_USER, nullable=False)
    max_uses: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
