from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.core.responses import success_response
from app.models.user import User
from app.schemas.file_asset import FileAssetPublic, FileUpdateRequest
from app.services.file_service import (
    decrypt_owned_file,
    get_owned_file,
    list_files,
    purge_file,
    restore_file,
    soft_delete_file,
    update_file_metadata,
    upload_file,
)

router = APIRouter()


@router.post("/upload")
async def upload_file_endpoint(
    file: UploadFile = File(...),
    folder_id: UUID | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    file_asset = await upload_file(session, owner=current_user, upload=file, folder_id=folder_id)
    return success_response(FileAssetPublic.model_validate(file_asset).model_dump(mode="json"))


@router.get("")
async def list_files_endpoint(
    folder_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    files = await list_files(session, current_user, folder_id=folder_id)
    return success_response([FileAssetPublic.model_validate(item).model_dump(mode="json") for item in files])


@router.get("/{file_id}")
async def get_file_endpoint(
    file_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    file_asset = await get_owned_file(session, current_user, file_id)
    return success_response(FileAssetPublic.model_validate(file_asset).model_dump(mode="json"))


@router.patch("/{file_id}")
async def update_file_endpoint(
    file_id: UUID,
    payload: FileUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    file_asset = await update_file_metadata(
        session,
        current_user,
        file_id,
        display_name=payload.display_name,
        folder_id=payload.folder_id,
        is_favorite=payload.is_favorite,
    )
    return success_response(FileAssetPublic.model_validate(file_asset).model_dump(mode="json"))


@router.get("/{file_id}/download")
async def download_file_endpoint(
    file_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    file_asset, plain_bytes = await decrypt_owned_file(session, current_user, file_id)
    headers = {"Content-Disposition": f'attachment; filename="{file_asset.original_filename}"'}
    return Response(content=plain_bytes, media_type=file_asset.mime_type or "application/octet-stream", headers=headers)


@router.delete("/{file_id}")
async def delete_file_endpoint(
    file_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    await soft_delete_file(session, current_user, file_id)
    return success_response(message="deleted")


@router.delete("/{file_id}/purge")
async def purge_file_endpoint(
    file_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    await purge_file(session, current_user, file_id)
    return success_response(message="purged")


@router.post("/{file_id}/restore")
async def restore_file_endpoint(
    file_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    file_asset = await restore_file(session, current_user, file_id)
    return success_response(FileAssetPublic.model_validate(file_asset).model_dump(mode="json"))
