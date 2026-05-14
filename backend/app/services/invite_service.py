from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.invite import Invite
from app.models.user import User
from app.schemas.invite import InviteCreateRequest
from app.services.audit_service import write_audit_log
from app.services.auth_service import generate_invite_code


async def create_invite(db: AsyncSession, payload: InviteCreateRequest, creator: User) -> Invite:
    if payload.expires_at is not None and payload.expires_at <= datetime.now(UTC):
        raise AppError("invalid_invite_expiry", "Invite expiration must be in the future", 400)
    if payload.role_to_assign not in {"admin", "user", "guest"}:
        raise AppError("invalid_role", "Invite role must be admin, user, or guest", 400)
    if payload.role_to_assign == "admin" and creator.role != "owner":
        raise AppError("owner_required", "Only the owner can create admin invites", 403)

    invite = Invite(
        invite_code=generate_invite_code(),
        created_by_user_id=creator.id,
        role_to_assign=payload.role_to_assign,
        max_uses=payload.max_uses,
        expires_at=payload.expires_at,
        note=payload.note,
    )
    db.add(invite)
    await db.flush()
    await write_audit_log(
        db,
        action="invite.create",
        actor_user_id=creator.id,
        target_type="invite",
        target_id=str(invite.id),
    )
    await db.commit()
    await db.refresh(invite)
    return invite


async def list_invites(db: AsyncSession, creator: User) -> list[Invite]:
    result = await db.scalars(
        select(Invite)
        .where(Invite.created_by_user_id == creator.id)
        .order_by(Invite.created_at.desc())
    )
    return list(result)
