from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID

from fastapi import UploadFile
from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.document_asset import DocumentAsset
from app.models.file_asset import FileAsset
from app.models.photo_asset import PhotoAsset
from app.models.receipt import Receipt
from app.models.user import User
from app.services.audit_service import write_audit_log
from app.services.file_service import create_encrypted_asset_from_bytes, decrypt_owned_file
from app.services.file_service import soft_delete_file


def _jpeg_bytes(image: Image.Image, max_size: tuple[int, int]) -> bytes:
    copy = ImageOps.exif_transpose(image.copy())
    copy.thumbnail(max_size)
    buffer = BytesIO()
    copy.convert("RGB").save(buffer, format="JPEG", quality=82, optimize=True)
    return buffer.getvalue()


async def upload_photo(db: AsyncSession, owner: User, upload: UploadFile) -> PhotoAsset:
    plain_bytes = await upload.read()
    if not plain_bytes:
        raise AppError("empty_file", "Uploaded photo is empty", 400)
    try:
        image = Image.open(BytesIO(plain_bytes))
        image.verify()
        image = Image.open(BytesIO(plain_bytes))
    except Exception as exc:
        raise AppError("invalid_photo", "Uploaded file is not a supported image", 400) from exc

    original_filename = upload.filename or "photo"
    original_asset = await create_encrypted_asset_from_bytes(
        db,
        owner=owner,
        plain_bytes=plain_bytes,
        original_filename=original_filename,
        mime_type=upload.content_type or "image/jpeg",
        source="mobile_upload",
        file_category="photo",
    )
    photo = await create_photo_record_for_asset(db, owner, original_asset, plain_bytes, image)
    from app.services.document_intelligence_service import enqueue_document_intelligence_task

    await enqueue_document_intelligence_task(db, owner=owner, file_asset=original_asset, source_type="photo")
    await write_audit_log(db, action="photo.upload", actor_user_id=owner.id, target_type="photo", target_id=str(photo.id))
    await db.commit()
    await db.refresh(photo)
    return photo


async def create_photo_record_for_asset(
    db: AsyncSession,
    owner: User,
    original_asset: FileAsset,
    plain_bytes: bytes,
    image: Image.Image | None = None,
) -> PhotoAsset:
    existing = await db.scalar(select(PhotoAsset).where(PhotoAsset.file_id == original_asset.id, PhotoAsset.owner_id == owner.id))
    if existing is not None:
        return existing
    if image is None:
        try:
            image = Image.open(BytesIO(plain_bytes))
            image.verify()
            image = Image.open(BytesIO(plain_bytes))
        except Exception as exc:
            raise AppError("invalid_photo", "Uploaded file is not a supported image", 400) from exc
    thumbnail_asset = await create_encrypted_asset_from_bytes(
        db,
        owner=owner,
        plain_bytes=_jpeg_bytes(image, (360, 360)),
        original_filename=f"{original_asset.id}-thumbnail.jpg",
        mime_type="image/jpeg",
        source="system_import",
        file_category="photo",
        derivative_type="thumbnail",
    )
    preview_asset = await create_encrypted_asset_from_bytes(
        db,
        owner=owner,
        plain_bytes=_jpeg_bytes(image, (1800, 1800)),
        original_filename=f"{original_asset.id}-preview.jpg",
        mime_type="image/jpeg",
        source="system_import",
        file_category="photo",
        derivative_type="preview",
    )
    exif = image.getexif()
    taken_at = None
    photo = PhotoAsset(
        owner_id=owner.id,
        file_id=original_asset.id,
        taken_at=taken_at,
        uploaded_at=datetime.now(UTC),
        width=image.width,
        height=image.height,
        orientation=exif.get(274) if exif else None,
        thumbnail_file_id=thumbnail_asset.id,
        preview_file_id=preview_asset.id,
    )
    db.add(photo)
    await db.flush()
    return photo


async def create_photo_from_file(db: AsyncSession, owner: User, file_id: UUID) -> PhotoAsset:
    existing = await db.scalar(select(PhotoAsset).where(PhotoAsset.file_id == file_id, PhotoAsset.owner_id == owner.id))
    if existing is not None:
        return existing
    original_asset, plain_bytes = await decrypt_owned_file(db, owner, file_id)
    photo = await create_photo_record_for_asset(db, owner, original_asset, plain_bytes)
    from app.services.document_intelligence_service import enqueue_document_intelligence_task

    await enqueue_document_intelligence_task(db, owner=owner, file_asset=original_asset, source_type="photo")
    await write_audit_log(db, action="photo.create_from_file", actor_user_id=owner.id, target_type="photo", target_id=str(photo.id))
    await db.commit()
    await db.refresh(photo)
    return photo


async def list_photos(db: AsyncSession, owner: User) -> list[PhotoAsset]:
    result = await db.scalars(
        select(PhotoAsset)
        .where(PhotoAsset.owner_id == owner.id)
        .order_by(PhotoAsset.taken_at.desc().nullslast(), PhotoAsset.uploaded_at.desc())
    )
    return list(result)


async def get_owned_photo(db: AsyncSession, owner: User, photo_id: UUID) -> PhotoAsset:
    photo = await db.scalar(select(PhotoAsset).where(PhotoAsset.id == photo_id, PhotoAsset.owner_id == owner.id))
    if photo is None:
        raise AppError("photo_not_found", "Photo not found", 404)
    return photo


async def decrypt_photo_variant(
    db: AsyncSession,
    owner: User,
    photo_id: UUID,
    variant: str,
) -> tuple[FileAsset, bytes]:
    photo = await get_owned_photo(db, owner, photo_id)
    file_id = photo.file_id
    if variant == "thumbnail" and photo.thumbnail_file_id:
        file_id = photo.thumbnail_file_id
    if variant == "preview" and photo.preview_file_id:
        file_id = photo.preview_file_id
    return await decrypt_owned_file(db, owner, file_id)


async def toggle_photo_favorite(db: AsyncSession, owner: User, photo_id: UUID, is_favorite: bool) -> PhotoAsset:
    photo = await get_owned_photo(db, owner, photo_id)
    photo.is_favorite = is_favorite
    await write_audit_log(db, action="photo.favorite", actor_user_id=owner.id, target_type="photo", target_id=str(photo.id))
    await db.commit()
    await db.refresh(photo)
    return photo


async def delete_photo(db: AsyncSession, owner: User, photo_id: UUID) -> None:
    photo = await get_owned_photo(db, owner, photo_id)
    original_file_id = photo.file_id
    derivative_file_ids = [photo.thumbnail_file_id, photo.preview_file_id]
    referenced = await db.scalar(select(Receipt.id).where(Receipt.owner_id == owner.id, Receipt.file_id == original_file_id).limit(1))
    if referenced is None:
        referenced = await db.scalar(select(DocumentAsset.id).where(DocumentAsset.owner_id == owner.id, DocumentAsset.file_id == original_file_id).limit(1))
    await db.delete(photo)
    await db.flush()
    for file_id in {item for item in derivative_file_ids if item is not None}:
        await soft_delete_file(db, owner, file_id)
    if referenced is None:
        await soft_delete_file(db, owner, original_file_id)
    await write_audit_log(db, action="photo.delete", actor_user_id=owner.id, target_type="photo", target_id=str(photo_id))
    await db.commit()
