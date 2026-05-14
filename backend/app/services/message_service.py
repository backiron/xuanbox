from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageCreateRequest
from app.services.audit_service import write_audit_log

VALID_MESSAGE_LEVELS = {"info", "success", "warning", "critical"}


async def create_message(db: AsyncSession, sender: User, payload: MessageCreateRequest) -> Message:
    level = payload.level.lower()
    if level not in VALID_MESSAGE_LEVELS:
        raise AppError("invalid_message_level", "Invalid message level", 400)
    recipient = None
    if payload.recipient_username:
        recipient = await db.scalar(
            select(User).where(or_(User.username == payload.recipient_username, User.email == payload.recipient_username))
        )
        if recipient is None:
            raise AppError("recipient_not_found", "Recipient not found", 404)
    message = Message(
        sender_user_id=sender.id,
        recipient_user_id=recipient.id if recipient else None,
        scope="user" if recipient else "broadcast",
        title=payload.title,
        body=payload.body,
        level=level,
    )
    db.add(message)
    await write_audit_log(db, action="admin.message.create", actor_user_id=sender.id, target_type="message")
    await db.commit()
    await db.refresh(message)
    return message


async def list_admin_messages(db: AsyncSession, *, limit: int = 100) -> list[Message]:
    result = await db.scalars(select(Message).order_by(Message.created_at.desc()).limit(min(limit, 300)))
    return list(result)


async def list_user_messages(db: AsyncSession, user: User, *, unread_only: bool = False) -> list[Message]:
    statement = (
        select(Message)
        .where(
            Message.archived_at.is_(None),
            or_(Message.recipient_user_id == user.id, Message.scope == "broadcast"),
        )
        .order_by(Message.created_at.desc())
    )
    if unread_only:
        statement = statement.where(Message.read_at.is_(None))
    result = await db.scalars(statement)
    return list(result)


async def unread_count(db: AsyncSession, user: User) -> int:
    count = await db.scalar(
        select(func.count(Message.id)).where(
            Message.archived_at.is_(None),
            Message.read_at.is_(None),
            or_(Message.recipient_user_id == user.id, Message.scope == "broadcast"),
        )
    )
    return int(count or 0)


async def mark_read(db: AsyncSession, user: User, message_id: UUID) -> Message:
    message = await db.scalar(
        select(Message).where(
            Message.id == message_id,
            Message.archived_at.is_(None),
            or_(Message.recipient_user_id == user.id, Message.scope == "broadcast"),
        )
    )
    if message is None:
        raise AppError("message_not_found", "Message not found", 404)
    if message.read_at is None:
        message.read_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(message)
    return message


async def archive_admin_message(db: AsyncSession, actor: User, message_id: UUID) -> None:
    message = await db.get(Message, message_id)
    if message is None:
        raise AppError("message_not_found", "Message not found", 404)
    message.archived_at = datetime.now(UTC)
    await write_audit_log(db, action="admin.message.archive", actor_user_id=actor.id, target_type="message", target_id=str(message.id))
    await db.commit()
