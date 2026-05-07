from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Receipt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "receipts"

    owner_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    file_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("file_assets.id", ondelete="CASCADE"), index=True, nullable=False)
    merchant: Mapped[str | None] = mapped_column(String(160), index=True, nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    purchase_date: Mapped[date | None] = mapped_column(Date(), index=True, nullable=True)
    warranty_until: Mapped[date | None] = mapped_column(Date(), index=True, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
