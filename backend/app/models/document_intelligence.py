from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class DocumentIntelligenceTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_intelligence_tasks"

    owner_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    file_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("file_assets.id", ondelete="CASCADE"), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), default="file", index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    detected_type: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_profiles"

    owner_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    file_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("file_assets.id", ondelete="CASCADE"), index=True, unique=True, nullable=False)
    task_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("document_intelligence_tasks.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_type: Mapped[str] = mapped_column(String(64), default="general", index=True, nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    counterparty: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    amount: Mapped[str | None] = mapped_column(String(64), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    warranty_until: Mapped[str | None] = mapped_column(String(32), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    keywords: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    labels: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentFieldValue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_field_values"
    __table_args__ = (UniqueConstraint("profile_id", "field_key", name="uq_document_field_values_profile_key"),)

    owner_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    file_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("file_assets.id", ondelete="CASCADE"), index=True, nullable=False)
    profile_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("document_profiles.id", ondelete="CASCADE"), index=True, nullable=False)
    field_key: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    field_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    field_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="rules", nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentTextChunk(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "document_text_chunks"

    owner_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    file_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("file_assets.id", ondelete="CASCADE"), index=True, nullable=False)
    task_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("document_intelligence_tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
