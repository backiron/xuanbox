from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.responses import success_response
from app.models.user import User
from app.schemas.folder import FolderCreateRequest, FolderPublic, FolderUpdateRequest
from app.services.folder_service import create_folder, delete_folder, list_folders, update_folder

router = APIRouter()


@router.get("")
async def list_folders_endpoint(
    parent_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    folders = await list_folders(session, current_user, parent_id)
    return success_response([FolderPublic.model_validate(folder).model_dump(mode="json") for folder in folders])


@router.post("")
async def create_folder_endpoint(
    payload: FolderCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    folder = await create_folder(session, current_user, payload)
    return success_response(FolderPublic.model_validate(folder).model_dump(mode="json"))


@router.patch("/{folder_id}")
async def update_folder_endpoint(
    folder_id: UUID,
    payload: FolderUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    folder = await update_folder(session, current_user, folder_id, payload)
    return success_response(FolderPublic.model_validate(folder).model_dump(mode="json"))


@router.delete("/{folder_id}")
async def delete_folder_endpoint(
    folder_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    await delete_folder(session, current_user, folder_id)
    return success_response(message="deleted")
