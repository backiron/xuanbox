"""XuanDrop conversations: instant transfer between a user's own devices and between contacts.

Attachments live outside the library (``encrypted_drop/``) and expire after ``DROP_RETENTION_DAYS``.
Saving an attachment copies it into the saving user's library, so the original can expire safely.
"""

from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import UploadFile
from PIL import Image, ImageOps
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.realtime import online_device_ids, publish_to_users
from app.models.auth_session import AuthSession
from app.models.device import Device
from app.models.drop import DropContact, DropMessage, DropMessageSave, DropThread, DropThreadMember
from app.models.user import User
from app.schemas.drop import DropSaveRequest, DropTextMessageRequest
from app.services.audit_service import write_audit_log
from app.services.encryption_service import decrypt_bytes, encrypt_bytes, generate_file_key, unwrap_file_key, wrap_file_key
from app.services.storage_service import delete_physical_file, read_encrypted_file, save_encrypted_file
from app.services.upload_limits import read_user_upload_bytes

THREAD_SELF = "self"
THREAD_DIRECT = "direct"
CONTACT_PENDING = "pending"
CONTACT_ACCEPTED = "accepted"
CONTACT_DECLINED = "declined"
MESSAGE_TEXT = "text"
MESSAGE_FILE = "file"
MAX_PAGE_SIZE = 100
THUMBNAIL_SIZE = (480, 480)
DROP_USER_ROLES = {"user", "guest"}


def _now() -> datetime:
    return datetime.now(UTC)


def _self_key(user_id: UUID) -> str:
    return f"self:{user_id}"


def _direct_key(first: UUID, second: UUID) -> str:
    low, high = sorted([str(first), str(second)])
    return f"direct:{low}:{high}"


def _user_brief(user: User) -> dict[str, Any]:
    return {"id": str(user.id), "username": user.username, "display_name": user.display_name or user.username}


def _drop_path(thread_id: UUID, message_id: UUID, suffix: str) -> Path:
    return Path(settings.STORAGE_ROOT) / "encrypted_drop" / str(thread_id) / f"{message_id}{suffix}"


# ---------------------------------------------------------------- devices


async def list_my_devices(db: AsyncSession, user: User, current_device_id: UUID | None) -> list[dict[str, Any]]:
    now = _now()
    active_device_ids = select(AuthSession.device_id).where(
        AuthSession.owner_id == user.id,
        AuthSession.is_active.is_(True),
        AuthSession.revoked_at.is_(None),
        AuthSession.expires_at > now,
        AuthSession.device_id.is_not(None),
    )
    devices = list(
        await db.scalars(
            select(Device)
            .where(Device.owner_id == user.id, Device.revoked_at.is_(None), Device.id.in_(active_device_ids))
            .order_by(Device.last_seen_at.desc().nullslast())
        )
    )
    online = await online_device_ids(device.id for device in devices)
    return [
        {
            "id": str(device.id),
            "device_name": device.device_name,
            "device_type": device.device_type,
            "last_seen_at": device.last_seen_at,
            "online": str(device.id) in online,
            "is_current": device.id == current_device_id,
        }
        for device in devices
    ]


async def rename_device(db: AsyncSession, user: User, device_id: UUID, device_name: str) -> Device:
    device = await db.scalar(select(Device).where(Device.id == device_id, Device.owner_id == user.id, Device.revoked_at.is_(None)))
    if device is None:
        raise AppError("device_not_found", "Device not found", 404)
    device.device_name = device_name.strip()
    await db.commit()
    await publish_to_users([user.id], "devices.changed", {})
    return device


async def remove_device(db: AsyncSession, user: User, device_id: UUID, current_device_id: UUID | None) -> None:
    from app.services.settings_service import revoke_device

    if device_id == current_device_id:
        raise AppError("cannot_remove_current_device", "Sign out on this device instead", 400)
    await revoke_device(db, user, device_id)
    await publish_to_users([user.id], "devices.changed", {})


# ---------------------------------------------------------------- contacts


async def are_contacts(db: AsyncSession, first: UUID, second: UUID) -> bool:
    contact_id = await db.scalar(
        select(DropContact.id).where(
            DropContact.status == CONTACT_ACCEPTED,
            or_(
                and_(DropContact.requester_id == first, DropContact.addressee_id == second),
                and_(DropContact.requester_id == second, DropContact.addressee_id == first),
            ),
        )
    )
    return contact_id is not None


async def _contact_public(db: AsyncSession, contact: DropContact, viewer: User) -> dict[str, Any]:
    peer_id = contact.addressee_id if contact.requester_id == viewer.id else contact.requester_id
    peer = await db.get(User, peer_id)
    return {
        "id": str(contact.id),
        "status": contact.status,
        "direction": "outgoing" if contact.requester_id == viewer.id else "incoming",
        "peer": _user_brief(peer) if peer else None,
        "created_at": contact.created_at,
        "responded_at": contact.responded_at,
    }


async def list_contacts(db: AsyncSession, user: User) -> list[dict[str, Any]]:
    contacts = await db.scalars(
        select(DropContact)
        .where(
            or_(DropContact.requester_id == user.id, DropContact.addressee_id == user.id),
            # A declined request is hidden from both sides; the requester can ask again later.
            DropContact.status != CONTACT_DECLINED,
        )
        .order_by(DropContact.created_at.desc())
    )
    return [await _contact_public(db, contact, user) for contact in contacts]


async def request_contact(db: AsyncSession, user: User, identifier: str) -> dict[str, Any]:
    value = identifier.strip()
    target = await db.scalar(
        select(User).where(or_(User.username == value, func.lower(User.email) == value.lower()))
    )
    if target is None or target.status != "active" or target.role not in DROP_USER_ROLES:
        raise AppError("contact_user_not_found", "No user with that username or email", 404)
    if target.id == user.id:
        raise AppError("contact_self", "You cannot add yourself", 400)

    outgoing = await db.scalar(select(DropContact).where(DropContact.requester_id == user.id, DropContact.addressee_id == target.id))
    incoming = await db.scalar(select(DropContact).where(DropContact.requester_id == target.id, DropContact.addressee_id == user.id))
    now = _now()
    if incoming is not None and incoming.status in {CONTACT_PENDING, CONTACT_ACCEPTED}:
        # They already asked us: asking back means yes.
        contact = incoming
        if contact.status == CONTACT_PENDING:
            contact.status = CONTACT_ACCEPTED
            contact.responded_at = now
    elif outgoing is not None:
        contact = outgoing
        if contact.status == CONTACT_DECLINED:
            contact.status = CONTACT_PENDING
            contact.responded_at = None
    else:
        contact = DropContact(requester_id=user.id, addressee_id=target.id, status=CONTACT_PENDING)
        db.add(contact)
    await db.flush()
    await write_audit_log(db, action="drop.contact_request", actor_user_id=user.id, target_type="user", target_id=str(target.id))
    await db.commit()
    await publish_to_users([user.id, target.id], "contacts.changed", {})
    return await _contact_public(db, contact, user)


async def _get_contact_for(db: AsyncSession, user: User, contact_id: UUID) -> DropContact:
    contact = await db.scalar(
        select(DropContact).where(
            DropContact.id == contact_id,
            or_(DropContact.requester_id == user.id, DropContact.addressee_id == user.id),
        )
    )
    if contact is None:
        raise AppError("contact_not_found", "Contact not found", 404)
    return contact


async def respond_contact(db: AsyncSession, user: User, contact_id: UUID, accept: bool) -> dict[str, Any]:
    contact = await _get_contact_for(db, user, contact_id)
    if contact.addressee_id != user.id or contact.status != CONTACT_PENDING:
        raise AppError("contact_not_pending", "Only a pending request sent to you can be answered", 400)
    contact.status = CONTACT_ACCEPTED if accept else CONTACT_DECLINED
    contact.responded_at = _now()
    await write_audit_log(
        db,
        action="drop.contact_accept" if accept else "drop.contact_decline",
        actor_user_id=user.id,
        target_type="drop_contact",
        target_id=str(contact.id),
    )
    await db.commit()
    await publish_to_users([contact.requester_id, contact.addressee_id], "contacts.changed", {})
    return await _contact_public(db, contact, user)


async def remove_contact(db: AsyncSession, user: User, contact_id: UUID) -> None:
    contact = await _get_contact_for(db, user, contact_id)
    members = [contact.requester_id, contact.addressee_id]
    await write_audit_log(db, action="drop.contact_remove", actor_user_id=user.id, target_type="drop_contact", target_id=str(contact.id))
    await db.delete(contact)
    await db.commit()
    await publish_to_users(members, "contacts.changed", {})


# ---------------------------------------------------------------- threads


async def _get_or_create_thread(db: AsyncSession, kind: str, key: str, member_ids: list[UUID]) -> DropThread:
    now = _now()
    await db.execute(
        pg_insert(DropThread)
        .values(id=uuid4(), kind=kind, thread_key=key, created_at=now, updated_at=now)
        .on_conflict_do_nothing(index_elements=["thread_key"])
    )
    thread = await db.scalar(select(DropThread).where(DropThread.thread_key == key))
    for member_id in member_ids:
        await db.execute(
            pg_insert(DropThreadMember)
            .values(thread_id=thread.id, user_id=member_id)
            .on_conflict_do_nothing(index_elements=["thread_id", "user_id"])
        )
    return thread


async def ensure_self_thread(db: AsyncSession, user: User) -> DropThread:
    thread = await _get_or_create_thread(db, THREAD_SELF, _self_key(user.id), [user.id])
    await db.commit()
    return thread


async def open_direct_thread(db: AsyncSession, user: User, peer_id: UUID) -> DropThread:
    if not await are_contacts(db, user.id, peer_id):
        raise AppError("not_contacts", "Add this person as a contact first", 403)
    thread = await _get_or_create_thread(db, THREAD_DIRECT, _direct_key(user.id, peer_id), [user.id, peer_id])
    await db.commit()
    return thread


async def _thread_peer_id(db: AsyncSession, thread: DropThread, user: User) -> UUID | None:
    if thread.kind != THREAD_DIRECT:
        return None
    return await db.scalar(
        select(DropThreadMember.user_id).where(DropThreadMember.thread_id == thread.id, DropThreadMember.user_id != user.id)
    )


async def _member_ids(db: AsyncSession, thread_id: UUID) -> list[UUID]:
    return list(await db.scalars(select(DropThreadMember.user_id).where(DropThreadMember.thread_id == thread_id)))


async def get_member_thread(db: AsyncSession, user: User, thread_id: UUID) -> tuple[DropThread, DropThreadMember]:
    row = (
        await db.execute(
            select(DropThread, DropThreadMember)
            .join(DropThreadMember, DropThreadMember.thread_id == DropThread.id)
            .where(DropThread.id == thread_id, DropThreadMember.user_id == user.id)
        )
    ).first()
    if row is None:
        raise AppError("drop_thread_not_found", "Conversation not found", 404)
    return row[0], row[1]


async def _ensure_can_send(db: AsyncSession, thread: DropThread, user: User) -> list[UUID]:
    members = await _member_ids(db, thread.id)
    if thread.kind == THREAD_DIRECT:
        peer_ids = [member for member in members if member != user.id]
        if not peer_ids or not await are_contacts(db, user.id, peer_ids[0]):
            raise AppError("not_contacts", "You are no longer contacts with this person", 403)
    return members


async def list_threads(db: AsyncSession, user: User, current_device_id: UUID | None) -> list[dict[str, Any]]:
    await ensure_self_thread(db, user)
    now = _now()
    rows = (
        await db.execute(
            select(DropThread, DropThreadMember)
            .join(DropThreadMember, DropThreadMember.thread_id == DropThread.id)
            .where(DropThreadMember.user_id == user.id)
            .order_by(DropThread.last_message_at.desc().nullslast(), DropThread.created_at.asc())
        )
    ).all()
    threads = []
    for thread, member in rows:
        alive = and_(DropMessage.thread_id == thread.id, DropMessage.expires_at > now)
        last_message = await db.scalar(select(DropMessage).where(alive).order_by(DropMessage.created_at.desc()).limit(1))
        if thread.kind == THREAD_SELF:
            # In "my devices", unread means sent from another device of mine.
            not_mine = or_(DropMessage.sender_device_id.is_(None), DropMessage.sender_device_id != current_device_id)
        else:
            not_mine = DropMessage.sender_user_id != user.id
        unread_filter = [alive, not_mine]
        if member.last_read_at is not None:
            unread_filter.append(DropMessage.created_at > member.last_read_at)
        unread = await db.scalar(select(func.count(DropMessage.id)).where(*unread_filter))
        peer_id = await _thread_peer_id(db, thread, user)
        peer = await db.get(User, peer_id) if peer_id else None
        threads.append(
            {
                "id": str(thread.id),
                "kind": thread.kind,
                "peer": _user_brief(peer) if peer else None,
                "can_send": thread.kind == THREAD_SELF or (peer_id is not None and await are_contacts(db, user.id, peer_id)),
                "last_message": message_public(last_message) if last_message else None,
                "last_message_at": thread.last_message_at,
                "last_read_at": member.last_read_at,
                "unread_count": int(unread or 0),
            }
        )
    return threads


async def mark_thread_read(db: AsyncSession, user: User, thread_id: UUID) -> datetime:
    thread, member = await get_member_thread(db, user, thread_id)
    member.last_read_at = _now()
    await db.commit()
    await publish_to_users(await _member_ids(db, thread.id), "thread.read", {"thread_id": str(thread.id), "user_id": str(user.id), "last_read_at": member.last_read_at})
    return member.last_read_at


# ---------------------------------------------------------------- messages


def message_public(message: DropMessage, saved_to: str | None = None) -> dict[str, Any]:
    return {
        "id": str(message.id),
        "thread_id": str(message.thread_id),
        "sender_user_id": str(message.sender_user_id),
        "sender_device_id": str(message.sender_device_id) if message.sender_device_id else None,
        "sender_label": message.sender_label,
        "target_device_id": str(message.target_device_id) if message.target_device_id else None,
        "client_id": message.client_id,
        "kind": message.kind,
        "body": message.body,
        "filename": message.filename,
        "mime_type": message.mime_type,
        "file_size": message.file_size,
        "has_thumbnail": bool(message.thumb_path),
        "image_width": message.image_width,
        "image_height": message.image_height,
        "created_at": message.created_at,
        "expires_at": message.expires_at,
        "saved_to": saved_to,
    }


async def list_messages(
    db: AsyncSession,
    user: User,
    thread_id: UUID,
    *,
    before: datetime | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    await get_member_thread(db, user, thread_id)
    statement = select(DropMessage).where(DropMessage.thread_id == thread_id, DropMessage.expires_at > _now())
    if before is not None:
        statement = statement.where(DropMessage.created_at < before)
    messages = list(await db.scalars(statement.order_by(DropMessage.created_at.desc()).limit(min(max(limit, 1), MAX_PAGE_SIZE))))
    messages.reverse()
    saves = {
        save.message_id: save.destination
        for save in await db.scalars(
            select(DropMessageSave).where(DropMessageSave.user_id == user.id, DropMessageSave.message_id.in_([m.id for m in messages]))
        )
    }
    return [message_public(message, saves.get(message.id)) for message in messages]


async def _validate_target_device(db: AsyncSession, thread: DropThread, user: User, target_device_id: UUID | None) -> None:
    if target_device_id is None:
        return
    if thread.kind != THREAD_SELF:
        raise AppError("invalid_target_device", "A target device can only be chosen between your own devices", 400)
    device_id = await db.scalar(
        select(Device.id).where(Device.id == target_device_id, Device.owner_id == user.id, Device.revoked_at.is_(None))
    )
    if device_id is None:
        raise AppError("invalid_target_device", "Target device not found", 400)


async def _finish_new_message(db: AsyncSession, thread: DropThread, members: list[UUID], message: DropMessage, user: User) -> dict[str, Any]:
    thread.last_message_at = message.created_at
    await write_audit_log(
        db,
        action=f"drop.message_{message.kind}",
        actor_user_id=user.id,
        target_type="drop_message",
        target_id=str(message.id),
        device_id=message.sender_device_id,
        metadata_json={"thread_id": str(thread.id), "size": message.file_size} if message.kind == MESSAGE_FILE else {"thread_id": str(thread.id)},
    )
    await db.commit()
    await db.refresh(message)
    data = message_public(message)
    await publish_to_users(members, "message.created", data)
    return data


async def send_text(db: AsyncSession, user: User, device_id: UUID | None, thread_id: UUID, payload: DropTextMessageRequest) -> dict[str, Any]:
    thread, _member = await get_member_thread(db, user, thread_id)
    members = await _ensure_can_send(db, thread, user)
    await _validate_target_device(db, thread, user, payload.target_device_id)
    now = _now()
    message = DropMessage(
        thread_id=thread.id,
        sender_user_id=user.id,
        sender_device_id=device_id,
        target_device_id=payload.target_device_id,
        client_id=payload.client_id,
        kind=MESSAGE_TEXT,
        body=payload.body,
        expires_at=now + timedelta(days=settings.DROP_RETENTION_DAYS),
        created_at=now,
    )
    db.add(message)
    await db.flush()
    return await _finish_new_message(db, thread, members, message, user)


async def _ensure_pending_capacity(db: AsyncSession, user: User, incoming: int) -> None:
    used = await db.scalar(
        select(func.coalesce(func.sum(DropMessage.file_size), 0)).where(
            DropMessage.sender_user_id == user.id,
            DropMessage.kind == MESSAGE_FILE,
            DropMessage.expires_at > _now(),
        )
    )
    if int(used or 0) + incoming > settings.DROP_USER_PENDING_LIMIT_MB * 1024 * 1024:
        raise AppError(
            "drop_pending_limit",
            "Too many unsaved transfers. Save or delete some, or wait for older ones to expire.",
            413,
        )


def _make_thumbnail(plain_bytes: bytes) -> tuple[bytes, int, int] | None:
    try:
        image = Image.open(BytesIO(plain_bytes))
        image = ImageOps.exif_transpose(image)
        width, height = image.size
        image.thumbnail(THUMBNAIL_SIZE)
        buffer = BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=80, optimize=True)
        return buffer.getvalue(), width, height
    except Exception:
        return None


async def send_file(
    db: AsyncSession,
    user: User,
    device_id: UUID | None,
    thread_id: UUID,
    upload: UploadFile,
    *,
    target_device_id: UUID | None = None,
    client_id: str | None = None,
    sender_label: str | None = None,
) -> dict[str, Any]:
    thread, _member = await get_member_thread(db, user, thread_id)
    members = await _ensure_can_send(db, thread, user)
    await _validate_target_device(db, thread, user, target_device_id)
    plain_bytes = await read_user_upload_bytes(upload)
    await _ensure_pending_capacity(db, user, len(plain_bytes))

    now = _now()
    message_id = uuid4()
    mime_type = upload.content_type or "application/octet-stream"
    file_key = generate_file_key()
    ciphertext, nonce, auth_tag = encrypt_bytes(plain_bytes, file_key)
    path = _drop_path(thread.id, message_id, ".bin")
    await save_encrypted_file(path, ciphertext)
    message = DropMessage(
        id=message_id,
        thread_id=thread.id,
        sender_user_id=user.id,
        sender_device_id=device_id,
        sender_label=sender_label,
        target_device_id=target_device_id,
        client_id=client_id,
        kind=MESSAGE_FILE,
        filename=(upload.filename or "file")[:255],
        mime_type=mime_type[:160],
        file_size=len(plain_bytes),
        encrypted_path=str(path),
        encrypted_file_key=wrap_file_key(file_key),
        nonce=nonce,
        auth_tag=auth_tag,
        expires_at=now + timedelta(days=settings.DROP_RETENTION_DAYS),
        created_at=now,
    )
    if mime_type.startswith("image/"):
        thumbnail = _make_thumbnail(plain_bytes)
        if thumbnail is not None:
            thumb_bytes, message.image_width, message.image_height = thumbnail
            thumb_key = generate_file_key()
            thumb_cipher, message.thumb_nonce, message.thumb_auth_tag = encrypt_bytes(thumb_bytes, thumb_key)
            thumb_path = _drop_path(thread.id, message_id, ".thumb.bin")
            await save_encrypted_file(thumb_path, thumb_cipher)
            message.thumb_path = str(thumb_path)
            message.thumb_file_key = wrap_file_key(thumb_key)
    db.add(message)
    try:
        await db.flush()
        return await _finish_new_message(db, thread, members, message, user)
    except Exception:
        _delete_message_blobs(message)
        raise


async def _get_member_message(db: AsyncSession, user: User, message_id: UUID) -> DropMessage:
    message = await db.scalar(
        select(DropMessage)
        .join(DropThreadMember, DropThreadMember.thread_id == DropMessage.thread_id)
        .where(DropMessage.id == message_id, DropThreadMember.user_id == user.id)
    )
    if message is None or message.expires_at <= _now():
        raise AppError("drop_message_not_found", "This transfer has expired or was deleted", 404)
    return message


def _decrypt_message_file(message: DropMessage) -> bytes:
    if message.kind != MESSAGE_FILE or not message.encrypted_path:
        raise AppError("drop_message_not_file", "This message has no file", 400)
    return decrypt_bytes(
        read_encrypted_file(message.encrypted_path),
        unwrap_file_key(message.encrypted_file_key),
        message.nonce,
        message.auth_tag,
    )


async def download_message_file(db: AsyncSession, user: User, message_id: UUID) -> tuple[DropMessage, bytes]:
    message = await _get_member_message(db, user, message_id)
    plain_bytes = _decrypt_message_file(message)
    await write_audit_log(db, action="drop.message_download", actor_user_id=user.id, target_type="drop_message", target_id=str(message.id))
    await db.commit()
    return message, plain_bytes


async def read_message_thumbnail(db: AsyncSession, user: User, message_id: UUID) -> bytes:
    message = await _get_member_message(db, user, message_id)
    if not message.thumb_path:
        raise AppError("drop_thumbnail_not_found", "No preview for this message", 404)
    return decrypt_bytes(
        read_encrypted_file(message.thumb_path),
        unwrap_file_key(message.thumb_file_key),
        message.thumb_nonce,
        message.thumb_auth_tag,
    )


def _delete_message_blobs(message: DropMessage) -> None:
    for path in (message.encrypted_path, message.thumb_path):
        if path:
            delete_physical_file(path)


async def delete_message(db: AsyncSession, user: User, message_id: UUID) -> None:
    message = await _get_member_message(db, user, message_id)
    if message.sender_user_id != user.id:
        raise AppError("drop_delete_denied", "Only the sender can delete this message", 403)
    members = await _member_ids(db, message.thread_id)
    data = {"id": str(message.id), "thread_id": str(message.thread_id)}
    _delete_message_blobs(message)
    await write_audit_log(db, action="drop.message_delete", actor_user_id=user.id, target_type="drop_message", target_id=str(message.id))
    await db.delete(message)
    await db.commit()
    await publish_to_users(members, "message.deleted", data)


async def save_message_to_library(db: AsyncSession, user: User, message_id: UUID, payload: DropSaveRequest) -> dict[str, Any]:
    from app.services.file_service import add_library_file
    from app.services.receipt_service import create_receipt_for_file

    message = await _get_member_message(db, user, message_id)
    existing = await db.scalar(select(DropMessageSave).where(DropMessageSave.message_id == message.id, DropMessageSave.user_id == user.id))
    if existing is not None:
        return message_public(message, existing.destination)
    if payload.destination == "photos" and not (message.mime_type or "").startswith("image/"):
        raise AppError("invalid_photo", "Only images can be saved to Photos", 400)

    plain_bytes = _decrypt_message_file(message)
    file_asset = await add_library_file(
        db,
        owner=user,
        plain_bytes=plain_bytes,
        original_filename=message.filename or "file",
        mime_type=message.mime_type,
        source="xuandrop",
    )
    db.add(DropMessageSave(message_id=message.id, user_id=user.id, destination=payload.destination, file_id=file_asset.id))
    await write_audit_log(
        db,
        action="drop.message_save",
        actor_user_id=user.id,
        target_type="drop_message",
        target_id=str(message.id),
        metadata_json={"destination": payload.destination, "file_id": str(file_asset.id)},
    )
    await db.flush()
    if payload.destination == "receipts":
        await create_receipt_for_file(db, user, file_asset.id, merchant=payload.merchant, category=payload.category)
    await db.commit()
    return message_public(message, payload.destination)


async def cleanup_expired_messages(db: AsyncSession, batch_size: int = 500) -> int:
    expired = list(
        await db.scalars(select(DropMessage).where(DropMessage.expires_at <= _now()).order_by(DropMessage.expires_at).limit(batch_size))
    )
    for message in expired:
        _delete_message_blobs(message)
    if expired:
        await db.execute(delete(DropMessage).where(DropMessage.id.in_([message.id for message in expired])))
    await db.commit()
    return len(expired)
