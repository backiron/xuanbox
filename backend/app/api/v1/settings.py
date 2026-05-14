from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.responses import success_response
from app.models.user import User
from app.schemas.settings import ProfileUpdateRequest
from app.schemas.user import UserPublic
from app.services.settings_service import get_avatar, revoke_device, storage_usage, update_profile, upload_avatar

router = APIRouter()


@router.patch("/profile")
async def update_profile_endpoint(
    payload: ProfileUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    user = await update_profile(
        session,
        current_user,
        display_name=payload.display_name,
        email=str(payload.email) if payload.email is not None else None,
    )
    return success_response(UserPublic.model_validate(user).model_dump(mode="json"))


@router.post("/avatar")
async def upload_avatar_endpoint(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    await upload_avatar(session, current_user, file)
    return success_response(UserPublic.model_validate(current_user).model_dump(mode="json"))


@router.get("/avatar")
async def avatar_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> Response:
    file_asset, plain_bytes = await get_avatar(session, current_user)
    return Response(content=plain_bytes, media_type=file_asset.mime_type or "image/jpeg")


@router.get("/storage")
async def storage_usage_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    usage = await storage_usage(session, current_user)
    return success_response(usage.model_dump(mode="json"))


@router.post("/devices/{device_id}/revoke")
async def revoke_device_endpoint(
    device_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    await revoke_device(session, current_user, device_id)
    return success_response(message="device revoked")
