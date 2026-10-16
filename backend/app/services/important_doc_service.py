"""The vault: files and photos kept behind a separate 6-digit PIN.

The PIN is an access gate on top of the normal per-file encryption, not a separate encryption key, so a
forgotten PIN can be reset with the account password without losing anything. Everything placed in the
vault disappears from the rest of the app (see vault_scope.py); its shares are revoked, it is removed from
albums, and text recognised from it is dropped so it cannot surface in search.
"""

import time
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any
from uuid import UUID

from fastapi import UploadFile
from PIL import Image, ImageOps
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.rate_limit import clear, count_failure, guard
from app.core.redis import redis_client
from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.models.album import Album, AlbumPhoto
from app.models.document_asset import DocumentAsset
from app.models.document_intelligence import DocumentFieldValue, DocumentIntelligenceTask, DocumentProfile, DocumentTextChunk
from app.models.file_asset import FileAsset
from app.models.photo_asset import PhotoAsset
from app.models.receipt import Receipt
from app.models.search_embedding import SearchEmbedding
from app.models.share import Share
from app.models.user import User
from app.services.audit_service import write_audit_log
from app.services.file_service import create_encrypted_asset_from_bytes, decrypt_file_asset, get_owned_file
from app.services.storage_service import delete_physical_file
from app.services.upload_limits import read_user_upload_bytes
from app.services.vault_scope import VAULT_LEVEL

VAULT_UNLOCK_SECONDS = 10 * 60
MAX_PIN_ATTEMPTS = 5
PIN_LOCK_MINUTES = 15
RESET_FAILURES = 5
RESET_WINDOW_SECONDS = 15 * 60
THUMBNAIL_SIZE = (480, 480)
INLINE_TYPES = ("image/", "application/pdf", "text/plain", "video/", "audio/")


def _now() -> datetime:
    return datetime.now(UTC)


def _epoch_key(user_id: UUID) -> str:
    return f"xb:vault:epoch:{user_id}"


# ---------------------------------------------------------------- PIN


def _pin_locked_until(owner: User) -> datetime | None:
    locked_until = owner.vault_pin_locked_until
    if locked_until and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=UTC)
    if locked_until and locked_until > _now():
        return locked_until
    return None


async def _check_pin(db: AsyncSession, owner: User, pin: str) -> None:
    if not owner.vault_pin_hash:
        raise AppError("vault_pin_not_set", "Set a vault PIN first", 400)
    if _pin_locked_until(owner):
        raise AppError("vault_pin_locked", "Too many incorrect PIN attempts. Try again in 15 minutes.", 423)
    if not verify_password(pin, owner.vault_pin_hash):
        owner.vault_pin_failed_attempts += 1
        if owner.vault_pin_failed_attempts >= MAX_PIN_ATTEMPTS:
            owner.vault_pin_locked_until = _now() + timedelta(minutes=PIN_LOCK_MINUTES)
        await write_audit_log(db, action="vault.pin_failed", actor_user_id=owner.id)
        await db.commit()
        raise AppError("invalid_vault_pin", "Incorrect PIN", 403)
    owner.vault_pin_failed_attempts = 0
    owner.vault_pin_locked_until = None


async def setup_vault_pin(db: AsyncSession, owner: User, pin: str) -> str:
    if owner.vault_pin_hash:
        raise AppError("vault_pin_exists", "A vault PIN is already set", 409)
    owner.vault_pin_hash = hash_password(pin)
    owner.vault_pin_failed_attempts = 0
    owner.vault_pin_locked_until = None
    await write_audit_log(db, action="vault.pin_setup", actor_user_id=owner.id)
    await db.commit()
    return create_vault_unlock_token(owner)


async def unlock_vault_pin(db: AsyncSession, owner: User, pin: str) -> str:
    await _check_pin(db, owner, pin)
    await write_audit_log(db, action="vault.unlock", actor_user_id=owner.id)
    await db.commit()
    return create_vault_unlock_token(owner)


async def change_vault_pin(db: AsyncSession, owner: User, current_pin: str, new_pin: str) -> str:
    await _check_pin(db, owner, current_pin)
    owner.vault_pin_hash = hash_password(new_pin)
    await write_audit_log(db, action="vault.pin_change", actor_user_id=owner.id)
    await db.commit()
    await lock_vault(owner)
    return create_vault_unlock_token(owner)


async def reset_vault_pin(db: AsyncSession, owner: User, password: str, new_pin: str) -> str:
    """Forgotten PIN: the account password proves who you are; vault contents are kept."""
    key = f"xb:rl:vault-reset:{owner.id}"
    await guard((key, RESET_FAILURES), message="Too many attempts. Wait 15 minutes and try again.")
    if not verify_password(password, owner.password_hash):
        await count_failure(key, RESET_WINDOW_SECONDS)
        await write_audit_log(db, action="vault.pin_reset_failed", actor_user_id=owner.id)
        await db.commit()
        raise AppError("invalid_password", "Incorrect account password", 403)
    await clear(key)
    owner.vault_pin_hash = hash_password(new_pin)
    owner.vault_pin_failed_attempts = 0
    owner.vault_pin_locked_until = None
    await write_audit_log(db, action="vault.pin_reset", actor_user_id=owner.id)
    await db.commit()
    await lock_vault(owner)
    return create_vault_unlock_token(owner)


def create_vault_unlock_token(owner: User) -> str:
    return create_access_token(
        str(owner.id),
        {
            "type": "vault_unlock",
            "scope": "important_docs",
            "unlocked_at": time.time(),
            "exp": int((_now() + timedelta(seconds=VAULT_UNLOCK_SECONDS)).timestamp()),
        },
    )


async def lock_vault(owner: User) -> None:
    """Invalidate every unlock issued so far, on all devices."""
    await redis_client.set(_epoch_key(owner.id), str(time.time()), ex=VAULT_UNLOCK_SECONDS + 60)


async def verify_vault_unlock_token(owner: User, token: str | None) -> None:
    if not owner.vault_pin_hash:
        raise AppError("vault_pin_not_set", "Set a vault PIN first", 400)
    if not token:
        raise AppError("vault_unlock_required", "Unlock the vault first", 401)
    payload = decode_token(token)
    if payload.get("type") != "vault_unlock" or payload.get("scope") != "important_docs" or payload.get("sub") != str(owner.id):
        raise AppError("invalid_vault_unlock", "Unlock the vault first", 401)
    epoch = await redis_client.get(_epoch_key(owner.id))
    if epoch and float(payload.get("unlocked_at") or 0) < float(epoch):
        raise AppError("vault_unlock_required", "The vault was locked", 401)


# ---------------------------------------------------------------- items


def _is_image(file_asset: FileAsset) -> bool:
    return (file_asset.mime_type or "").startswith("image/")


async def _item(db: AsyncSession, document: DocumentAsset, file_asset: FileAsset | None = None) -> dict[str, Any]:
    file_asset = file_asset or await db.get(FileAsset, document.file_id)
    photo_id = await db.scalar(select(PhotoAsset.id).where(PhotoAsset.file_id == document.file_id).limit(1))
    return {
        "id": str(document.id),
        "file_id": str(document.file_id),
        "title": document.title,
        "note": document.note,
        "document_type": document.document_type,
        "expires_at": document.expires_at.isoformat() if document.expires_at else None,
        "filename": file_asset.original_filename if file_asset else None,
        "mime_type": file_asset.mime_type if file_asset else None,
        "file_size": file_asset.file_size if file_asset else None,
        "is_image": bool(file_asset and _is_image(file_asset)),
        "from_photos": photo_id is not None,
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
    }


async def list_vault_items(db: AsyncSession, owner: User) -> list[dict[str, Any]]:
    rows = await db.execute(
        select(DocumentAsset, FileAsset)
        .join(FileAsset, FileAsset.id == DocumentAsset.file_id)
        .where(DocumentAsset.owner_id == owner.id, DocumentAsset.security_level == VAULT_LEVEL)
        .order_by(DocumentAsset.created_at.desc())
    )
    return [await _item(db, document, file_asset) for document, file_asset in rows.all()]


async def _get_vault_document(db: AsyncSession, owner: User, document_id: UUID) -> DocumentAsset:
    document = await db.scalar(
        select(DocumentAsset).where(DocumentAsset.id == document_id, DocumentAsset.owner_id == owner.id, DocumentAsset.security_level == VAULT_LEVEL)
    )
    if document is None:
        raise AppError("vault_item_not_found", "Not found in the vault", 404)
    return document


async def _seal(db: AsyncSession, owner: User, file_id: UUID) -> None:
    """Cut every way the file could still be reached outside the vault."""
    photo = await db.scalar(select(PhotoAsset).where(PhotoAsset.owner_id == owner.id, PhotoAsset.file_id == file_id))
    share_targets = [file_id] + ([photo.id] if photo else [])
    await db.execute(
        update(Share)
        .where(Share.owner_id == owner.id, Share.target_id.in_(share_targets), Share.target_type.in_(("file", "document", "photo")))
        .values(is_active=False)
    )
    if photo:
        album_ids = list(await db.scalars(select(AlbumPhoto.album_id).where(AlbumPhoto.photo_id == photo.id)))
        await db.execute(delete(AlbumPhoto).where(AlbumPhoto.photo_id == photo.id))
        hidden = [item for item in (photo.file_id, photo.thumbnail_file_id, photo.preview_file_id) if item]
        for album in await db.scalars(select(Album).where(Album.id.in_(album_ids), Album.cover_file_id.in_(hidden))):
            album.cover_file_id = None
    # Recognised text and fields would otherwise still be searchable.
    await db.execute(delete(SearchEmbedding).where(SearchEmbedding.owner_id == owner.id, SearchEmbedding.file_id == file_id))
    await db.execute(delete(DocumentTextChunk).where(DocumentTextChunk.owner_id == owner.id, DocumentTextChunk.file_id == file_id))
    await db.execute(delete(DocumentFieldValue).where(DocumentFieldValue.owner_id == owner.id, DocumentFieldValue.file_id == file_id))
    await db.execute(delete(DocumentProfile).where(DocumentProfile.owner_id == owner.id, DocumentProfile.file_id == file_id))
    await db.execute(delete(DocumentIntelligenceTask).where(DocumentIntelligenceTask.owner_id == owner.id, DocumentIntelligenceTask.file_id == file_id))


async def place_file_in_vault(db: AsyncSession, owner: User, file_asset: FileAsset, title: str | None = None) -> DocumentAsset:
    """Move a library or inbox file into the vault. Does not commit."""
    if await db.scalar(select(Receipt.id).where(Receipt.owner_id == owner.id, Receipt.file_id == file_asset.id).limit(1)):
        raise AppError("vault_receipt_file", "This file belongs to a receipt. Delete the receipt first.", 409)
    document = await db.scalar(select(DocumentAsset).where(DocumentAsset.owner_id == owner.id, DocumentAsset.file_id == file_asset.id))
    if document is None:
        document = DocumentAsset(owner_id=owner.id, file_id=file_asset.id, document_type="other", title=(title or file_asset.display_name)[:180])
        db.add(document)
    document.security_level = VAULT_LEVEL
    await db.flush()
    await _seal(db, owner, file_asset.id)
    await write_audit_log(db, action="vault.add", actor_user_id=owner.id, target_type="file", target_id=str(file_asset.id))
    return document


async def add_file_to_vault(db: AsyncSession, owner: User, file_id: UUID, title: str | None = None) -> dict[str, Any]:
    file_asset = await get_owned_file(db, owner, file_id)
    document = await place_file_in_vault(db, owner, file_asset, title)
    await db.commit()
    await db.refresh(document)
    return await _item(db, document, file_asset)


async def upload_to_vault(db: AsyncSession, owner: User, upload: UploadFile) -> dict[str, Any]:
    """Straight into the vault: never shown in the library, never recognised or indexed."""
    plain_bytes = await read_user_upload_bytes(upload)
    filename = upload.filename or "file"
    file_asset = await create_encrypted_asset_from_bytes(
        db, owner=owner, plain_bytes=plain_bytes, original_filename=filename, mime_type=upload.content_type, source="vault_upload"
    )
    document = DocumentAsset(owner_id=owner.id, file_id=file_asset.id, document_type="other", title=filename[:180], security_level=VAULT_LEVEL)
    db.add(document)
    await write_audit_log(db, action="vault.upload", actor_user_id=owner.id, target_type="file", target_id=str(file_asset.id))
    await db.commit()
    await db.refresh(document)
    return await _item(db, document, file_asset)


async def rename_vault_item(db: AsyncSession, owner: User, document_id: UUID, title: str | None, note: str | None) -> dict[str, Any]:
    document = await _get_vault_document(db, owner, document_id)
    if title is not None and title.strip():
        document.title = title.strip()[:180]
    if note is not None:
        document.note = note.strip() or None
    await db.commit()
    await db.refresh(document)
    return await _item(db, document)


async def read_vault_item(db: AsyncSession, owner: User, document_id: UUID) -> tuple[DocumentAsset, FileAsset, bytes]:
    document = await _get_vault_document(db, owner, document_id)
    file_asset = await get_owned_file(db, owner, document.file_id, allow_vault_locked=True)
    plain_bytes = decrypt_file_asset(file_asset)
    document.last_viewed_at = _now()
    await write_audit_log(db, action="vault.open", actor_user_id=owner.id, target_type="document", target_id=str(document.id))
    await db.commit()
    return document, file_asset, plain_bytes


def is_inline_type(mime_type: str | None) -> bool:
    return bool(mime_type) and mime_type.startswith(INLINE_TYPES) and mime_type != "image/svg+xml"


async def vault_thumbnail(db: AsyncSession, owner: User, document_id: UUID) -> bytes:
    document = await _get_vault_document(db, owner, document_id)
    file_asset = await get_owned_file(db, owner, document.file_id, allow_vault_locked=True)
    if not _is_image(file_asset):
        raise AppError("vault_no_thumbnail", "No preview for this file", 404)
    photo = await db.scalar(select(PhotoAsset).where(PhotoAsset.owner_id == owner.id, PhotoAsset.file_id == file_asset.id))
    if photo and photo.thumbnail_file_id:
        thumbnail = await db.get(FileAsset, photo.thumbnail_file_id)
        if thumbnail:
            return decrypt_file_asset(thumbnail)
    try:
        image = ImageOps.exif_transpose(Image.open(BytesIO(decrypt_file_asset(file_asset))))
        image.thumbnail(THUMBNAIL_SIZE)
        buffer = BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=80)
        return buffer.getvalue()
    except Exception as exc:
        raise AppError("vault_no_thumbnail", "No preview for this file", 404) from exc


async def remove_from_vault(db: AsyncSession, owner: User, document_id: UUID) -> dict[str, Any]:
    """Back to the library: a photo returns to Photos, anything else to Files."""
    document = await _get_vault_document(db, owner, document_id)
    file_asset = await get_owned_file(db, owner, document.file_id, allow_vault_locked=True)
    await db.delete(document)
    await db.flush()
    photo = await db.scalar(select(PhotoAsset).where(PhotoAsset.owner_id == owner.id, PhotoAsset.file_id == file_asset.id))
    destination = "photos" if photo else "files"
    if file_asset.source == "vault_upload":
        file_asset.source = "manual_upload"
        if file_asset.file_category == "photo" and photo is None:
            from app.services.photo_service import create_photo_record_for_asset

            await create_photo_record_for_asset(db, owner, file_asset, decrypt_file_asset(file_asset))
            destination = "photos"
    if destination == "files":
        from app.services.document_intelligence_service import enqueue_document_intelligence_task

        await enqueue_document_intelligence_task(db, owner=owner, file_asset=file_asset, source_type=file_asset.file_category)
    await write_audit_log(db, action="vault.remove", actor_user_id=owner.id, target_type="file", target_id=str(file_asset.id))
    await db.commit()
    return {"destination": destination}


async def delete_vault_item(db: AsyncSession, owner: User, document_id: UUID) -> None:
    """Delete for good: the file, and the photo and its thumbnail/preview if it came from Photos."""
    document = await _get_vault_document(db, owner, document_id)
    file_asset = await get_owned_file(db, owner, document.file_id, allow_vault_locked=True)
    files = [file_asset]
    photo = await db.scalar(select(PhotoAsset).where(PhotoAsset.owner_id == owner.id, PhotoAsset.file_id == file_asset.id))
    if photo:
        for variant_id in (photo.thumbnail_file_id, photo.preview_file_id):
            variant = await db.get(FileAsset, variant_id) if variant_id else None
            if variant:
                files.append(variant)
        await db.delete(photo)
    await db.delete(document)
    await db.execute(delete(Share).where(Share.owner_id == owner.id, Share.target_id.in_([file_asset.id] + ([photo.id] if photo else []))))
    await db.flush()
    paths = [item.encrypted_path for item in files]
    for item in files:
        await db.delete(item)
    await write_audit_log(db, action="vault.delete", actor_user_id=owner.id, target_type="file", target_id=str(file_asset.id))
    await db.commit()
    for path in paths:
        delete_physical_file(path)
