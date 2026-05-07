import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import USER_ROLE_OWNER, USER_STATUS_ACTIVE
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.auth_session import AuthSession
from app.models.invite import Invite
from app.models.user import User
from app.schemas.auth import BootstrapOwnerRequest, InviteRegisterRequest, LoginRequest, TokenPair
from app.services.audit_service import write_audit_log
from app.services.device_service import create_login_device


def build_token_pair(user: User, session_id: UUID, refresh_token: str) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(
            str(user.id),
            extra_claims={"role": user.role, "session_id": str(session_id)},
        ),
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def create_auth_session(
    db: AsyncSession,
    *,
    user: User,
    request: Request,
    device_name: str | None = None,
) -> TokenPair:
    device = await create_login_device(db, owner_id=user.id, request=request, device_name=device_name)
    refresh_token = generate_refresh_token()
    auth_session = AuthSession(
        owner_id=user.id,
        device_id=device.id,
        refresh_token_hash=hash_token(refresh_token),
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(auth_session)
    await db.flush()
    await write_audit_log(
        db,
        action="auth.login",
        actor_user_id=user.id,
        target_type="device",
        target_id=str(device.id),
        ip_address=device.last_ip,
        device_id=device.id,
        user_agent=request.headers.get("user-agent"),
    )
    return build_token_pair(user, auth_session.id, refresh_token)


async def bootstrap_owner(db: AsyncSession, payload: BootstrapOwnerRequest, request: Request) -> TokenPair:
    user_count = await db.scalar(select(func.count(User.id)))
    if user_count:
        raise AppError("bootstrap_closed", "Owner bootstrap is only available before the first user exists", 403)

    owner = User(
        username=payload.username,
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        role=USER_ROLE_OWNER,
        status=USER_STATUS_ACTIVE,
    )
    db.add(owner)
    await db.flush()
    tokens = await create_auth_session(db, user=owner, request=request, device_name=payload.device_name)
    await write_audit_log(db, action="auth.bootstrap_owner", actor_user_id=owner.id, target_type="user", target_id=str(owner.id))
    await db.commit()
    return tokens


async def register_by_invite(db: AsyncSession, payload: InviteRegisterRequest, request: Request) -> TokenPair:
    invite = await db.scalar(select(Invite).where(Invite.invite_code == payload.invite_code))
    now = datetime.now(UTC)
    if (
        invite is None
        or not invite.is_active
        or invite.used_count >= invite.max_uses
        or (invite.expires_at is not None and invite.expires_at <= now)
    ):
        raise AppError("invalid_invite", "Invite is invalid or expired", 400)

    existing = await db.scalar(
        select(User).where(or_(User.username == payload.username, User.email == str(payload.email)))
    )
    if existing is not None:
        raise AppError("user_exists", "Username or email already exists", 409)

    user = User(
        username=payload.username,
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        role=invite.role_to_assign,
        status=USER_STATUS_ACTIVE,
    )
    invite.used_count += 1
    if invite.used_count >= invite.max_uses:
        invite.is_active = False
    db.add(user)
    await db.flush()
    tokens = await create_auth_session(db, user=user, request=request, device_name=payload.device_name)
    await write_audit_log(
        db,
        action="auth.register_by_invite",
        actor_user_id=user.id,
        target_type="invite",
        target_id=str(invite.id),
    )
    await db.commit()
    return tokens


async def login(db: AsyncSession, payload: LoginRequest, request: Request) -> TokenPair:
    user = await db.scalar(
        select(User).where(or_(User.username == payload.username_or_email, User.email == payload.username_or_email))
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        await write_audit_log(
            db,
            action="auth.login_failed",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata_json={"username_or_email": payload.username_or_email},
        )
        await db.commit()
        raise AppError("invalid_credentials", "Invalid username/email or password", 401)
    if user.status != USER_STATUS_ACTIVE:
        raise AppError("user_inactive", "User is inactive", 403)

    user.last_login_at = datetime.now(UTC)
    tokens = await create_auth_session(db, user=user, request=request, device_name=payload.device_name)
    await db.commit()
    return tokens


async def refresh(db: AsyncSession, refresh_token: str) -> TokenPair:
    token_hash = hash_token(refresh_token)
    auth_session = await db.scalar(select(AuthSession).where(AuthSession.refresh_token_hash == token_hash))
    now = datetime.now(UTC)
    if (
        auth_session is None
        or not auth_session.is_active
        or auth_session.revoked_at is not None
        or auth_session.expires_at <= now
    ):
        raise AppError("invalid_refresh_token", "Refresh token is invalid or expired", 401)

    user = await db.get(User, auth_session.owner_id)
    if user is None or user.status != USER_STATUS_ACTIVE:
        raise AppError("user_inactive", "User is inactive or does not exist", 401)

    new_refresh_token = generate_refresh_token()
    auth_session.refresh_token_hash = hash_token(new_refresh_token)
    auth_session.expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await write_audit_log(db, action="auth.refresh", actor_user_id=user.id, target_type="session", target_id=str(auth_session.id))
    await db.commit()
    return build_token_pair(user, auth_session.id, new_refresh_token)


async def logout(db: AsyncSession, refresh_token: str | None, user: User) -> None:
    if refresh_token:
        auth_session = await db.scalar(select(AuthSession).where(AuthSession.refresh_token_hash == hash_token(refresh_token)))
        if auth_session and auth_session.owner_id == user.id:
            auth_session.is_active = False
            auth_session.revoked_at = datetime.now(UTC)
    await write_audit_log(db, action="auth.logout", actor_user_id=user.id)
    await db.commit()


async def logout_all_devices(db: AsyncSession, user: User) -> None:
    sessions = await db.scalars(select(AuthSession).where(AuthSession.owner_id == user.id, AuthSession.is_active.is_(True)))
    now = datetime.now(UTC)
    for auth_session in sessions:
        auth_session.is_active = False
        auth_session.revoked_at = now
    await write_audit_log(db, action="auth.logout_all_devices", actor_user_id=user.id)
    await db.commit()


def generate_invite_code() -> str:
    return secrets.token_urlsafe(18)
