import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.models.document_asset import DocumentAsset
from app.models.album import Album
from app.models.file_asset import FileAsset
from app.models.photo_asset import PhotoAsset
from app.models.receipt import Receipt
from app.models.share import Share, ShareAccessLog
from app.models.user import User
from app.schemas.share import ShareCreateRequest, ShareUpdateRequest
from app.services.file_service import decrypt_file_asset

ALLOWED_TARGET_TYPES = {"file", "photo", "receipt", "document", "album"}
ALLOWED_PERMISSIONS = {"read", "download", "upload", "comment"}
DOWNLOADABLE_TARGET_TYPES = {"file", "photo", "receipt", "document"}
DEFAULT_PUBLIC_SHARE_DAYS = 7
DEFAULT_PUBLIC_MAX_DOWNLOADS = 3
SHARE_ACCESS_SECONDS = 10 * 60


async def _find_shared_user(db: AsyncSession, username_or_email: str | None) -> User | None:
    if not username_or_email:
        return None
    return await db.scalar(
        select(User).where(or_(User.username == username_or_email, User.email == username_or_email))
    )


async def _target_exists(db: AsyncSession, owner: User, target_type: str, target_id: UUID) -> bool:
    if target_type in {"file", "document"}:
        statement = select(FileAsset).where(FileAsset.id == target_id, FileAsset.owner_id == owner.id, FileAsset.is_deleted.is_(False))
        if target_type == "document":
            statement = statement.where(FileAsset.file_category == "document")
        return await db.scalar(statement) is not None
    if target_type == "photo":
        return await db.scalar(select(PhotoAsset).where(PhotoAsset.id == target_id, PhotoAsset.owner_id == owner.id)) is not None
    if target_type == "receipt":
        return await db.scalar(select(Receipt).where(Receipt.id == target_id, Receipt.owner_id == owner.id)) is not None
    if target_type == "album":
        return await db.scalar(select(Album).where(Album.id == target_id, Album.owner_id == owner.id)) is not None
    return False


async def _is_vault_locked_target(db: AsyncSession, owner: User, target_type: str, target_id: UUID) -> bool:
    if target_type == "document":
        document = await db.scalar(
            select(DocumentAsset).where(
                DocumentAsset.file_id == target_id,
                DocumentAsset.owner_id == owner.id,
                DocumentAsset.security_level == "vault_locked",
            )
        )
        return document is not None
    if target_type == "file":
        document = await db.scalar(
            select(DocumentAsset).where(
                DocumentAsset.file_id == target_id,
                DocumentAsset.owner_id == owner.id,
                DocumentAsset.security_level == "vault_locked",
            )
        )
        return document is not None
    return False


async def _target_file(db: AsyncSession, share: Share) -> FileAsset:
    if share.target_type in {"file", "document"}:
        file_asset = await db.scalar(
            select(FileAsset).where(FileAsset.id == share.target_id, FileAsset.owner_id == share.owner_id, FileAsset.is_deleted.is_(False))
        )
        if file_asset is None:
            raise AppError("share_target_not_found", "Shared file is no longer available", 404)
        return file_asset
    if share.target_type == "photo":
        photo = await db.scalar(select(PhotoAsset).where(PhotoAsset.id == share.target_id, PhotoAsset.owner_id == share.owner_id))
        if photo is None:
            raise AppError("share_target_not_found", "Shared photo is no longer available", 404)
        file_asset = await db.get(FileAsset, photo.file_id)
        if file_asset is None or file_asset.is_deleted:
            raise AppError("share_target_not_found", "Shared photo file is no longer available", 404)
        return file_asset
    if share.target_type == "receipt":
        receipt = await db.scalar(select(Receipt).where(Receipt.id == share.target_id, Receipt.owner_id == share.owner_id))
        if receipt is None:
            raise AppError("share_target_not_found", "Shared receipt is no longer available", 404)
        file_asset = await db.get(FileAsset, receipt.file_id)
        if file_asset is None or file_asset.is_deleted:
            raise AppError("share_target_not_found", "Shared receipt file is no longer available", 404)
        return file_asset
    raise AppError("share_not_downloadable", "This share cannot be downloaded", 400)


async def target_name(db: AsyncSession, share: Share) -> str | None:
    if share.target_type in {"file", "document"}:
        file_asset = await db.get(FileAsset, share.target_id)
        return file_asset.display_name if file_asset else None
    if share.target_type == "photo":
        photo = await db.get(PhotoAsset, share.target_id)
        if photo is None:
            return None
        file_asset = await db.get(FileAsset, photo.file_id)
        return file_asset.display_name if file_asset else "Photo"
    if share.target_type == "receipt":
        receipt = await db.get(Receipt, share.target_id)
        if receipt is None:
            return None
        return receipt.merchant or "Receipt"
    if share.target_type == "album":
        album = await db.get(Album, share.target_id)
        return album.title if album else None
    return None


async def list_created_shares(db: AsyncSession, owner: User, *, archived: bool = False) -> list[Share]:
    statement = select(Share).where(Share.owner_id == owner.id)
    statement = statement.where(Share.archived_at.is_not(None) if archived else Share.archived_at.is_(None))
    result = await db.scalars(statement.order_by(Share.created_at.desc()))
    return list(result)


async def list_received_shares(db: AsyncSession, user: User) -> list[Share]:
    result = await db.scalars(select(Share).where(Share.shared_with_user_id == user.id).order_by(Share.created_at.desc()))
    return list(result)


async def create_share(db: AsyncSession, owner: User, payload: ShareCreateRequest) -> Share:
    target_type = payload.target_type.lower()
    permission = payload.permission.lower()
    if target_type not in ALLOWED_TARGET_TYPES:
        raise AppError("invalid_share_target", "Unsupported share target type", 400)
    if permission not in ALLOWED_PERMISSIONS:
        raise AppError("invalid_share_permission", "Unsupported share permission", 400)
    if not await _target_exists(db, owner, target_type, payload.target_id):
        raise AppError("share_target_not_found", "Share target not found", 404)

    shared_user = await _find_shared_user(db, payload.shared_with_username)
    if payload.shared_with_username and shared_user is None:
        raise AppError("shared_user_not_found", "Shared user not found", 404)
    if shared_user is None and await _is_vault_locked_target(db, owner, target_type, payload.target_id):
        raise AppError("public_share_denied_for_vault", "Important docs cannot be shared through a public link", 403)
    expires_at = payload.expires_at
    max_downloads = payload.max_downloads
    if shared_user is None:
        expires_at = expires_at or (datetime.now(UTC) + timedelta(days=DEFAULT_PUBLIC_SHARE_DAYS))
        max_downloads = max_downloads or DEFAULT_PUBLIC_MAX_DOWNLOADS

    share = Share(
        owner_id=owner.id,
        target_type=target_type,
        target_id=payload.target_id,
        shared_with_user_id=shared_user.id if shared_user else None,
        public_token=secrets.token_urlsafe(32),
        permission=permission,
        password_hash=hash_password(payload.password) if payload.password else None,
        max_downloads=max_downloads,
        expires_at=expires_at,
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)
    return share


async def get_owned_share(db: AsyncSession, owner: User, share_id: UUID) -> Share:
    share = await db.scalar(select(Share).where(Share.id == share_id, Share.owner_id == owner.id))
    if share is None:
        raise AppError("share_not_found", "Share not found", 404)
    return share


async def update_share(db: AsyncSession, owner: User, share_id: UUID, payload: ShareUpdateRequest) -> Share:
    share = await get_owned_share(db, owner, share_id)
    if payload.permission is not None:
        permission = payload.permission.lower()
        if permission not in ALLOWED_PERMISSIONS:
            raise AppError("invalid_share_permission", "Unsupported share permission", 400)
        share.permission = permission
    if "password" in payload.model_fields_set:
        share.password_hash = hash_password(payload.password) if payload.password else None
    if "max_downloads" in payload.model_fields_set:
        share.max_downloads = payload.max_downloads
    if "expires_at" in payload.model_fields_set:
        share.expires_at = payload.expires_at
    if payload.is_active is not None:
        share.is_active = payload.is_active
    await db.commit()
    await db.refresh(share)
    return share


async def deactivate_share(db: AsyncSession, owner: User, share_id: UUID) -> None:
    share = await get_owned_share(db, owner, share_id)
    share.is_active = False
    await db.commit()


def is_archiveable(share: Share) -> bool:
    return (
        not share.is_active
        or _is_expired(share)
        or (share.max_downloads is not None and share.download_count >= share.max_downloads)
    )


async def archive_share(db: AsyncSession, owner: User, share_id: UUID) -> None:
    share = await get_owned_share(db, owner, share_id)
    if not is_archiveable(share):
        raise AppError("share_archive_denied", "Only inactive, expired, or completed shares can be archived", 400)
    share.archived_at = datetime.now(UTC)
    await db.commit()


async def archive_inactive_shares(db: AsyncSession, owner: User) -> int:
    shares = await list_created_shares(db, owner)
    archiveable = [share for share in shares if is_archiveable(share)]
    for share in archiveable:
        share.archived_at = datetime.now(UTC)
    await db.commit()
    return len(archiveable)


def _is_expired(share: Share) -> bool:
    return share.expires_at is not None and share.expires_at <= datetime.now(UTC)


async def write_share_access_log(
    db: AsyncSession,
    share: Share,
    *,
    action: str,
    success: bool,
    ip_address: str | None,
    user_agent: str | None,
    actor_user_id: UUID | None = None,
    failure_reason: str | None = None,
) -> None:
    db.add(
        ShareAccessLog(
            share_id=share.id,
            actor_user_id=actor_user_id,
            action=action,
            success=success,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.now(UTC),
        )
    )
    await db.flush()


async def get_public_share(db: AsyncSession, token: str, *, action: str, ip_address: str | None, user_agent: str | None) -> Share:
    share = await db.scalar(select(Share).where(Share.public_token == token))
    if share is None:
        raise AppError("share_not_found", "Share not found", 404)
    failure_reason = None
    if not share.is_active:
        failure_reason = "inactive"
    elif _is_expired(share):
        failure_reason = "expired"
    elif share.max_downloads is not None and share.download_count >= share.max_downloads:
        failure_reason = "download_limit_reached"
    if failure_reason:
        await write_share_access_log(db, share, action=action, success=False, ip_address=ip_address, user_agent=user_agent, failure_reason=failure_reason)
        await db.commit()
        raise AppError(f"share_{failure_reason}", "Share is no longer available", 403)
    return share


async def verify_share_password(db: AsyncSession, share: Share, password: str | None, *, ip_address: str | None, user_agent: str | None) -> None:
    if not share.password_hash:
        return
    if not password or not verify_password(password, share.password_hash):
        await write_share_access_log(db, share, action="password.verify", success=False, ip_address=ip_address, user_agent=user_agent, failure_reason="invalid_password")
        await db.commit()
        raise AppError("invalid_share_password", "Invalid share password", 403)


def create_share_access_token(share: Share) -> str:
    expires_at = datetime.now(UTC) + timedelta(seconds=SHARE_ACCESS_SECONDS)
    return create_access_token(
        str(share.id),
        {
            "type": "share_access",
            "share_id": str(share.id),
            "exp": int(expires_at.timestamp()),
        },
    )


def verify_share_access_token(share: Share, token: str | None) -> None:
    if not share.password_hash:
        return
    if not token:
        raise AppError("share_access_required", "Unlock this share first", 403)
    payload = decode_token(token)
    if payload.get("type") != "share_access" or payload.get("share_id") != str(share.id):
        raise AppError("invalid_share_access", "Share access has expired or is invalid", 403)


async def public_share_metadata(db: AsyncSession, share: Share) -> tuple[str, FileAsset | None]:
    name = await target_name(db, share)
    file_asset = None
    if share.target_type in DOWNLOADABLE_TARGET_TYPES:
        file_asset = await _target_file(db, share)
    return name or "Shared item", file_asset


async def download_public_share(
    db: AsyncSession,
    share: Share,
    *,
    password: str | None,
    access_token: str | None,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[FileAsset, bytes]:
    if share.permission not in {"download", "read"}:
        await write_share_access_log(db, share, action="share.download", success=False, ip_address=ip_address, user_agent=user_agent, failure_reason="permission_denied")
        await db.commit()
        raise AppError("share_download_denied", "This share does not allow downloads", 403)
    if share.password_hash:
        if access_token:
            verify_share_access_token(share, access_token)
        else:
            await verify_share_password(db, share, password, ip_address=ip_address, user_agent=user_agent)
    file_asset = await _target_file(db, share)
    plain_bytes = decrypt_file_asset(file_asset)
    share.download_count += 1
    await write_share_access_log(db, share, action="share.download", success=True, ip_address=ip_address, user_agent=user_agent)
    await db.commit()
    await db.refresh(share)
    return file_asset, plain_bytes
