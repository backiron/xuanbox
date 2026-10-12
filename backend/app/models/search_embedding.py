from uuid import UUID

from sqlalchemy import ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class SearchEmbedding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One meaning vector for a piece of a user's own text (a receipt, or a chunk of a document)."""

    __tablename__ = "search_embeddings"
    __table_args__ = (UniqueConstraint("source_type", "source_id", "chunk_index", name="uq_search_embeddings_source_chunk"),)

    owner_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    # Deleting the underlying file removes its vectors.
    file_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("file_assets.id", ondelete="CASCADE"), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), index=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    vector: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
