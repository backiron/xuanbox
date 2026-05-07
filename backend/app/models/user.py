from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import USER_ROLE_USER, USER_STATUS_ACTIVE
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    avatar_file_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    role: Mapped[str] = mapped_column(String(32), default=USER_ROLE_USER, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=USER_STATUS_ACTIVE, nullable=False)
    storage_limit_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    devices = relationship("Device", back_populates="owner", cascade="all, delete-orphan")
    files = relationship("FileAsset", back_populates="owner")
    auth_sessions = relationship("AuthSession", back_populates="owner", cascade="all, delete-orphan")
