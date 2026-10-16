"""What the vault hides.

A vault item is a document with security level ``vault_locked``. Its file is hidden everywhere outside the
vault, and so is everything derived from it: a photo made from that file, and the photo's thumbnail and
preview, which are separate files.
"""

from uuid import UUID

from sqlalchemy import Select, or_, select, union
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_asset import DocumentAsset
from app.models.photo_asset import PhotoAsset

VAULT_LEVEL = "vault_locked"


def vault_document_file_ids(owner_id: UUID) -> Select:
    return select(DocumentAsset.file_id).where(DocumentAsset.owner_id == owner_id, DocumentAsset.security_level == VAULT_LEVEL)


def vault_photo_ids(owner_id: UUID) -> Select:
    return select(PhotoAsset.id).where(PhotoAsset.owner_id == owner_id, PhotoAsset.file_id.in_(vault_document_file_ids(owner_id)))


def vault_file_ids(owner_id: UUID):
    """Every file id the vault hides: vault files plus the thumbnails and previews of vault photos."""
    vault_photos = PhotoAsset.file_id.in_(vault_document_file_ids(owner_id))
    return union(
        vault_document_file_ids(owner_id),
        select(PhotoAsset.thumbnail_file_id).where(PhotoAsset.owner_id == owner_id, vault_photos, PhotoAsset.thumbnail_file_id.is_not(None)),
        select(PhotoAsset.preview_file_id).where(PhotoAsset.owner_id == owner_id, vault_photos, PhotoAsset.preview_file_id.is_not(None)),
    )


async def is_vault_file(db: AsyncSession, owner_id: UUID, file_id: UUID) -> bool:
    source_file_id = await db.scalar(
        select(PhotoAsset.file_id)
        .where(PhotoAsset.owner_id == owner_id, or_(PhotoAsset.thumbnail_file_id == file_id, PhotoAsset.preview_file_id == file_id))
        .limit(1)
    )
    candidates = [file_id] + ([source_file_id] if source_file_id else [])
    hit = await db.scalar(
        select(DocumentAsset.id)
        .where(DocumentAsset.owner_id == owner_id, DocumentAsset.security_level == VAULT_LEVEL, DocumentAsset.file_id.in_(candidates))
        .limit(1)
    )
    return hit is not None
