"""files photos albums tags

Revision ID: 0003_files_photos
Revises: 0002_auth_audit
Create Date: 2026-05-07 00:20:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_files_photos"
down_revision: str | None = "0002_auth_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "folders",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("path_cache", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["folders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_folders_owner_id"), "folders", ["owner_id"], unique=False)

    op.create_table(
        "tags",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "name", name="uq_tags_owner_name"),
    )
    op.create_index(op.f("ix_tags_owner_id"), "tags", ["owner_id"], unique=False)

    op.create_table(
        "photo_assets",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("camera_model", sa.String(length=160), nullable=True),
        sa.Column("orientation", sa.Integer(), nullable=True),
        sa.Column("exif_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("location_lat_encrypted", sa.String(length=255), nullable=True),
        sa.Column("location_lng_encrypted", sa.String(length=255), nullable=True),
        sa.Column("location_text", sa.String(length=255), nullable=True),
        sa.Column("thumbnail_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("preview_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["file_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["preview_file_id"], ["file_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["thumbnail_file_id"], ["file_assets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_photo_assets_file_id"), "photo_assets", ["file_id"], unique=True)
    op.create_index(op.f("ix_photo_assets_owner_id"), "photo_assets", ["owner_id"], unique=False)
    op.create_index(op.f("ix_photo_assets_taken_at"), "photo_assets", ["taken_at"], unique=False)
    op.create_index(op.f("ix_photo_assets_uploaded_at"), "photo_assets", ["uploaded_at"], unique=False)

    op.create_table(
        "albums",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cover_file_id"], ["file_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_albums_owner_id"), "albums", ["owner_id"], unique=False)

    op.create_table(
        "album_photos",
        sa.Column("album_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("photo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["photo_id"], ["photo_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("album_id", "photo_id", name="uq_album_photo"),
    )
    op.create_index(op.f("ix_album_photos_album_id"), "album_photos", ["album_id"], unique=False)
    op.create_index(op.f("ix_album_photos_photo_id"), "album_photos", ["photo_id"], unique=False)

    op.create_table(
        "tag_links",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tag_id", "target_type", "target_id", name="uq_tag_target"),
    )
    op.create_index(op.f("ix_tag_links_owner_id"), "tag_links", ["owner_id"], unique=False)
    op.create_index(op.f("ix_tag_links_tag_id"), "tag_links", ["tag_id"], unique=False)
    op.create_index(op.f("ix_tag_links_target_id"), "tag_links", ["target_id"], unique=False)
    op.create_index(op.f("ix_tag_links_target_type"), "tag_links", ["target_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tag_links_target_type"), table_name="tag_links")
    op.drop_index(op.f("ix_tag_links_target_id"), table_name="tag_links")
    op.drop_index(op.f("ix_tag_links_tag_id"), table_name="tag_links")
    op.drop_index(op.f("ix_tag_links_owner_id"), table_name="tag_links")
    op.drop_table("tag_links")
    op.drop_index(op.f("ix_album_photos_photo_id"), table_name="album_photos")
    op.drop_index(op.f("ix_album_photos_album_id"), table_name="album_photos")
    op.drop_table("album_photos")
    op.drop_index(op.f("ix_albums_owner_id"), table_name="albums")
    op.drop_table("albums")
    op.drop_index(op.f("ix_photo_assets_uploaded_at"), table_name="photo_assets")
    op.drop_index(op.f("ix_photo_assets_taken_at"), table_name="photo_assets")
    op.drop_index(op.f("ix_photo_assets_owner_id"), table_name="photo_assets")
    op.drop_index(op.f("ix_photo_assets_file_id"), table_name="photo_assets")
    op.drop_table("photo_assets")
    op.drop_index(op.f("ix_tags_owner_id"), table_name="tags")
    op.drop_table("tags")
    op.drop_index(op.f("ix_folders_owner_id"), table_name="folders")
    op.drop_table("folders")
