import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import hash_token
from app.models.transfer import TransferItem, TransferSession
from app.models.user import User
from app.schemas.transfer import TransferSaveRequest, TransferSessionCreateRequest
from app.services.audit_service import write_audit_log
from app.services.file_service import upload_file
from app.services.photo_service import create_photo_from_file
from app.services.receipt_service import create_receipt_for_file


async def create_transfer_session(db: AsyncSession, owner: User, payload: TransferSessionCreateRequest) -> tuple[TransferSession, str]:
    token = secrets.token_urlsafe(24)
    session = TransferSession(
        owner_id=owner.id,
        token_hash=hash_token(token),
        title=payload.title,
        expires_at=datetime.now(UTC) + timedelta(minutes=payload.expires_in_minutes),
    )
    db.add(session)
    await db.flush()
    await write_audit_log(db, action="drop.session_create", actor_user_id=owner.id, target_type="transfer_session", target_id=str(session.id))
    await db.commit()
    await db.refresh(session)
    return session, token


async def list_transfer_sessions(db: AsyncSession, owner: User) -> list[TransferSession]:
    result = await db.scalars(
        select(TransferSession).where(TransferSession.owner_id == owner.id).order_by(TransferSession.created_at.desc())
    )
    return list(result)


async def get_owned_session(db: AsyncSession, owner: User, session_id: UUID) -> TransferSession:
    session = await db.scalar(select(TransferSession).where(TransferSession.id == session_id, TransferSession.owner_id == owner.id))
    if session is None:
        raise AppError("drop_session_not_found", "Transfer session not found", 404)
    return session


async def get_open_session_by_token(db: AsyncSession, token: str) -> TransferSession:
    session = await db.scalar(select(TransferSession).where(TransferSession.token_hash == hash_token(token)))
    now = datetime.now(UTC)
    if session is None or session.status != "open" or session.expires_at <= now:
        raise AppError("drop_session_closed", "Transfer session is closed or expired", 404)
    return session


async def upload_transfer_item(db: AsyncSession, token: str, upload: UploadFile) -> TransferItem:
    session = await get_open_session_by_token(db, token)
    owner = await db.get(User, session.owner_id)
    if owner is None:
        raise AppError("owner_not_found", "Transfer owner no longer exists", 404)
    file_asset = await upload_file(db, owner=owner, upload=upload, source="xuandrop_upload")
    item = TransferItem(
        session_id=session.id,
        owner_id=owner.id,
        file_id=file_asset.id,
        original_filename=file_asset.original_filename,
        mime_type=file_asset.mime_type,
        file_size=file_asset.file_size,
    )
    db.add(item)
    await db.flush()
    await write_audit_log(db, action="drop.upload", actor_user_id=owner.id, target_type="transfer_session", target_id=str(session.id))
    await db.commit()
    await db.refresh(item)
    return item


async def list_transfer_items(db: AsyncSession, owner: User, session_id: UUID) -> list[TransferItem]:
    await get_owned_session(db, owner, session_id)
    result = await db.scalars(
        select(TransferItem)
        .where(TransferItem.session_id == session_id, TransferItem.owner_id == owner.id)
        .order_by(TransferItem.created_at.desc())
    )
    return list(result)


async def save_transfer_item(db: AsyncSession, owner: User, item_id: UUID, payload: TransferSaveRequest) -> TransferItem:
    item = await db.scalar(select(TransferItem).where(TransferItem.id == item_id, TransferItem.owner_id == owner.id))
    if item is None:
        raise AppError("drop_item_not_found", "Transfer item not found", 404)
    if payload.destination == "photos":
        await create_photo_from_file(db, owner, item.file_id)
    elif payload.destination == "receipts":
        await create_receipt_for_file(db, owner, item.file_id, merchant=payload.merchant, category=payload.category)
    item.status = "saved"
    item.saved_to = payload.destination
    await write_audit_log(db, action="drop.save_item", actor_user_id=owner.id, target_type="transfer_item", target_id=str(item.id))
    await db.commit()
    await db.refresh(item)
    return item
