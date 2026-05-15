from uuid import UUID
from datetime import UTC, datetime

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.auth_session import AuthSession
from app.models.device import Device
from app.models.file_asset import FileAsset
from app.models.user import User
from app.schemas.settings import StorageUsagePublic
from app.services.audit_service import write_audit_log
from app.services.file_service import create_encrypted_asset_from_bytes, decrypt_file_asset
from app.services.upload_limits import MAX_AVATAR_UPLOAD_BYTES, read_upload_bytes


async def update_profile(db: AsyncSession, user: User, *, display_name: str | None, email: str | None) -> User:
    if email is not None and email != user.email:
        existing = await db.scalar(select(User).where(User.email == email, User.id != user.id))
        if existing is not None:
            raise AppError("email_exists", "Email is already in use", 409)
        user.email = email
    if display_name is not None:
        user.display_name = display_name.strip() or None
    await write_audit_log(db, action="settings.profile.update", actor_user_id=user.id, target_type="user", target_id=str(user.id))
    await db.commit()
    await db.refresh(user)
    return user


async def upload_avatar(db: AsyncSession, user: User, upload: UploadFile) -> FileAsset:
    content = await read_upload_bytes(
        upload,
        max_bytes=MAX_AVATAR_UPLOAD_BYTES,
        empty_error_code="empty_avatar",
        empty_message="Avatar image is empty",
        too_large_error_code="avatar_too_large",
    )
    if upload.content_type and not upload.content_type.startswith("image/"):
        raise AppError("invalid_avatar_type", "Avatar must be an image", 400)
    avatar = await create_encrypted_asset_from_bytes(
        db,
        owner=user,
        plain_bytes=content,
        original_filename=upload.filename or "avatar",
        mime_type=upload.content_type,
        source="avatar",
        file_category="avatar",
    )
    user.avatar_file_id = avatar.id
    await write_audit_log(db, action="settings.avatar.update", actor_user_id=user.id, target_type="file", target_id=str(avatar.id))
    await db.commit()
    await db.refresh(user)
    await db.refresh(avatar)
    return avatar


async def get_avatar(db: AsyncSession, user: User) -> tuple[FileAsset, bytes]:
    if user.avatar_file_id is None:
        raise AppError("avatar_not_set", "Avatar is not set", 404)
    file_asset = await db.scalar(
        select(FileAsset).where(FileAsset.id == user.avatar_file_id, FileAsset.owner_id == user.id, FileAsset.is_deleted.is_(False))
    )
    if file_asset is None:
        raise AppError("avatar_not_found", "Avatar is not available", 404)
    return file_asset, decrypt_file_asset(file_asset)


async def storage_usage(db: AsyncSession, user: User) -> StorageUsagePublic:
    used = await db.scalar(
        select(func.coalesce(func.sum(FileAsset.file_size), 0)).where(
            FileAsset.owner_id == user.id,
            FileAsset.is_deleted.is_(False),
        )
    )
    used_bytes = int(used or 0)
    limit = user.storage_limit_bytes
    remaining = None if limit is None else max(0, limit - used_bytes)
    percent = None if not limit else min(100, round((used_bytes / limit) * 100))
    return StorageUsagePublic(used_bytes=used_bytes, limit_bytes=limit, remaining_bytes=remaining, percent_used=percent)


async def revoke_device(db: AsyncSession, user: User, device_id: UUID) -> None:
    device = await db.scalar(select(Device).where(Device.id == device_id, Device.owner_id == user.id))
    if device is None:
        raise AppError("device_not_found", "Device not found", 404)
    now = datetime.now(UTC)
    device.revoked_at = now
    sessions = await db.scalars(
        select(AuthSession).where(
            AuthSession.owner_id == user.id,
            AuthSession.device_id == device.id,
            AuthSession.is_active.is_(True),
        )
    )
    for session in sessions:
        session.is_active = False
        session.revoked_at = now
    await write_audit_log(db, action="settings.device.revoke", actor_user_id=user.id, target_type="device", target_id=str(device.id))
    await db.commit()
