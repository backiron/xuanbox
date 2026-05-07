import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.file_asset import FileAsset
from app.models.user import User
from app.services.audit_service import write_audit_log
from app.services.encryption_service import (
    decrypt_bytes,
    encrypt_bytes,
    generate_file_key,
    unwrap_file_key,
    wrap_file_key,
)
from app.services.storage_service import (
    delete_physical_file,
    encrypted_derivative_path,
    encrypted_file_path,
    read_encrypted_file,
    save_encrypted_file,
)


def detect_file_category(mime_type: str | None, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if mime_type and mime_type.startswith("image/"):
        return "photo"
    if mime_type and mime_type.startswith("video/"):
        return "video"
    if suffix in {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"}:
        return "document"
    if suffix in {".zip", ".rar", ".7z", ".tar", ".gz"}:
        return "archive"
    return "other"


async def upload_file(
    db: AsyncSession,
    *,
    owner: User,
    upload: UploadFile,
    source: str = "manual_upload",
    folder_id: UUID | None = None,
) -> FileAsset:
    plain_bytes = await upload.read()
    if not plain_bytes:
        raise AppError("empty_file", "Uploaded file is empty", 400)

    original_filename = upload.filename or str(uuid4())
    file_asset = await create_encrypted_asset_from_bytes(
        db,
        owner=owner,
        plain_bytes=plain_bytes,
        original_filename=original_filename,
        mime_type=upload.content_type,
        source=source,
        folder_id=folder_id,
    )
    await write_audit_log(
        db,
        action="file.upload",
        actor_user_id=owner.id,
        target_type="file",
        target_id=str(file_asset.id),
        metadata_json={"filename": original_filename, "size": len(plain_bytes)},
    )
    await db.commit()
    await db.refresh(file_asset)
    return file_asset


async def create_encrypted_asset_from_bytes(
    db: AsyncSession,
    *,
    owner: User,
    plain_bytes: bytes,
    original_filename: str,
    mime_type: str | None,
    source: str,
    folder_id: UUID | None = None,
    file_category: str | None = None,
    derivative_type: str | None = None,
) -> FileAsset:
    file_id = uuid4()
    file_key = generate_file_key()
    encrypted_payload, nonce, auth_tag = encrypt_bytes(plain_bytes, file_key)
    path = (
        encrypted_derivative_path(owner.id, file_id, derivative_type)
        if derivative_type
        else encrypted_file_path(owner.id, file_id)
    )
    await save_encrypted_file(path, encrypted_payload)
    file_asset = FileAsset(
        id=file_id,
        owner_id=owner.id,
        folder_id=folder_id,
        original_filename=original_filename,
        display_name=original_filename,
        mime_type=mime_type,
        file_ext=Path(original_filename).suffix.lower().lstrip(".") or None,
        file_size=len(plain_bytes),
        sha256_hash=hashlib.sha256(plain_bytes).hexdigest(),
        encrypted_path=str(path),
        encrypted_file_key=wrap_file_key(file_key),
        nonce=nonce,
        auth_tag=auth_tag,
        file_category=file_category or detect_file_category(mime_type, original_filename),
        source=source,
    )
    db.add(file_asset)
    await db.flush()
    return file_asset


async def list_files(
    db: AsyncSession,
    owner: User,
    include_deleted: bool = False,
    folder_id: UUID | None = None,
) -> list[FileAsset]:
    statement = select(FileAsset).where(FileAsset.owner_id == owner.id)
    if not include_deleted:
        statement = statement.where(FileAsset.is_deleted.is_(False))
    if folder_id is not None:
        statement = statement.where(FileAsset.folder_id == folder_id)
    result = await db.scalars(statement.order_by(FileAsset.created_at.desc()))
    return list(result)


async def get_owned_file(db: AsyncSession, owner: User, file_id: UUID, allow_deleted: bool = False) -> FileAsset:
    file_asset = await db.scalar(
        select(FileAsset).where(FileAsset.id == file_id, FileAsset.owner_id == owner.id)
    )
    if file_asset is None or (file_asset.is_deleted and not allow_deleted):
        raise AppError("file_not_found", "File not found", 404)
    return file_asset


async def decrypt_owned_file(db: AsyncSession, owner: User, file_id: UUID) -> tuple[FileAsset, bytes]:
    file_asset = await get_owned_file(db, owner, file_id)
    file_key = unwrap_file_key(file_asset.encrypted_file_key)
    ciphertext = read_encrypted_file(file_asset.encrypted_path)
    plain_bytes = decrypt_bytes(ciphertext, file_key, file_asset.nonce, file_asset.auth_tag)
    await write_audit_log(db, action="file.download", actor_user_id=owner.id, target_type="file", target_id=str(file_id))
    await db.commit()
    return file_asset, plain_bytes


async def soft_delete_file(db: AsyncSession, owner: User, file_id: UUID) -> None:
    file_asset = await get_owned_file(db, owner, file_id)
    file_asset.is_deleted = True
    file_asset.deleted_at = datetime.now(UTC)
    await write_audit_log(db, action="file.delete", actor_user_id=owner.id, target_type="file", target_id=str(file_id))
    await db.commit()


async def update_file_metadata(
    db: AsyncSession,
    owner: User,
    file_id: UUID,
    *,
    display_name: str | None = None,
    folder_id: UUID | None = None,
    is_favorite: bool | None = None,
) -> FileAsset:
    file_asset = await get_owned_file(db, owner, file_id)
    if display_name is not None:
        file_asset.display_name = display_name
    if folder_id is not None:
        file_asset.folder_id = folder_id
    if is_favorite is not None:
        file_asset.is_favorite = is_favorite
    await write_audit_log(db, action="file.update", actor_user_id=owner.id, target_type="file", target_id=str(file_id))
    await db.commit()
    await db.refresh(file_asset)
    return file_asset


async def restore_file(db: AsyncSession, owner: User, file_id: UUID) -> FileAsset:
    file_asset = await get_owned_file(db, owner, file_id, allow_deleted=True)
    file_asset.is_deleted = False
    file_asset.deleted_at = None
    await write_audit_log(db, action="file.restore", actor_user_id=owner.id, target_type="file", target_id=str(file_id))
    await db.commit()
    await db.refresh(file_asset)
    return file_asset


async def list_trash(db: AsyncSession, owner: User) -> list[FileAsset]:
    result = await db.scalars(
        select(FileAsset)
        .where(FileAsset.owner_id == owner.id, FileAsset.is_deleted.is_(True))
        .order_by(FileAsset.deleted_at.desc().nullslast())
    )
    return list(result)


async def purge_file(db: AsyncSession, owner: User, file_id: UUID) -> None:
    file_asset = await get_owned_file(db, owner, file_id, allow_deleted=True)
    if not file_asset.is_deleted:
        raise AppError("file_not_deleted", "Only deleted files can be purged", 400)
    delete_physical_file(file_asset.encrypted_path)
    await write_audit_log(db, action="file.purge", actor_user_id=owner.id, target_type="file", target_id=str(file_id))
    await db.delete(file_asset)
    await db.commit()
