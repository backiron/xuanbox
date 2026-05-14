"""document intelligence profile fields

Revision ID: 0015_doc_intel_profiles
Revises: 0014_document_intelligence
Create Date: 2026-05-13 02:20:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0015_doc_intel_profiles"
down_revision: str | None = "0014_document_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("document_profiles", sa.Column("counterparty", sa.String(length=255), nullable=True))
    op.add_column("document_profiles", sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("document_profiles", sa.Column("ai_summary", sa.Text(), nullable=True))
    op.add_column("document_profiles", sa.Column("ai_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.create_table(
        "document_field_values",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_key", sa.String(length=80), nullable=False),
        sa.Column("field_label", sa.String(length=120), nullable=True),
        sa.Column("field_value", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["file_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["document_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_field_values_field_key"), "document_field_values", ["field_key"], unique=False)
    op.create_index(op.f("ix_document_field_values_file_id"), "document_field_values", ["file_id"], unique=False)
    op.create_index(op.f("ix_document_field_values_owner_id"), "document_field_values", ["owner_id"], unique=False)
    op.create_index(op.f("ix_document_field_values_profile_id"), "document_field_values", ["profile_id"], unique=False)
    op.create_unique_constraint("uq_document_field_values_profile_key", "document_field_values", ["profile_id", "field_key"])


def downgrade() -> None:
    op.drop_constraint("uq_document_field_values_profile_key", "document_field_values", type_="unique")
    op.drop_index(op.f("ix_document_field_values_profile_id"), table_name="document_field_values")
    op.drop_index(op.f("ix_document_field_values_owner_id"), table_name="document_field_values")
    op.drop_index(op.f("ix_document_field_values_file_id"), table_name="document_field_values")
    op.drop_index(op.f("ix_document_field_values_field_key"), table_name="document_field_values")
    op.drop_table("document_field_values")
    op.drop_column("document_profiles", "ai_metadata")
    op.drop_column("document_profiles", "ai_summary")
    op.drop_column("document_profiles", "labels")
    op.drop_column("document_profiles", "counterparty")
