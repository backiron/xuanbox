from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.core.responses import success_response
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import (
    BootstrapOwnerRequest,
    ChangePasswordRequest,
    InviteRegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
)
from app.schemas.user import UserPublic
from app.services import auth_service
from app.services.audit_service import write_audit_log
from app.core.errors import AppError

router = APIRouter()


@router.post("/bootstrap-owner")
async def bootstrap_owner(
    payload: BootstrapOwnerRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    tokens = await auth_service.bootstrap_owner(session, payload, request)
    return success_response(tokens.model_dump())


@router.post("/register-by-invite")
async def register_by_invite(
    payload: InviteRegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    tokens = await auth_service.register_by_invite(session, payload, request)
    return success_response(tokens.model_dump())


@router.post("/login")
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    tokens = await auth_service.login(session, payload, request)
    return success_response(tokens.model_dump())


@router.post("/refresh")
async def refresh(
    payload: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    tokens = await auth_service.refresh(session, payload.refresh_token)
    return success_response(tokens.model_dump())


@router.post("/logout")
async def logout(
    payload: RefreshTokenRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    await auth_service.logout(session, payload.refresh_token if payload else None, current_user)
    return success_response(message="logged out")


@router.post("/logout-all-devices")
async def logout_all_devices(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    await auth_service.logout_all_devices(session, current_user)
    return success_response(message="logged out from all devices")


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not verify_password(payload.old_password, current_user.password_hash):
        raise AppError("invalid_password", "Old password is invalid", 400)
    current_user.password_hash = hash_password(payload.new_password)
    await auth_service.logout_all_devices(session, current_user)
    await write_audit_log(session, action="auth.change_password", actor_user_id=current_user.id)
    await session.commit()
    return success_response(message="password changed")


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)) -> dict:
    return success_response(UserPublic.model_validate(current_user).model_dump(mode="json"))
