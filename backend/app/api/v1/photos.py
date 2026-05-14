from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.responses import success_response
from app.models.user import User
from app.schemas.photo import PhotoPublic
from app.services.photo_service import delete_photo, decrypt_photo_variant, list_photos, toggle_photo_favorite, upload_photo

router = APIRouter()


@router.get("")
async def list_photos_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    photos = await list_photos(session, current_user)
    return success_response([PhotoPublic.model_validate(photo).model_dump(mode="json") for photo in photos])


@router.post("/upload")
async def upload_photo_endpoint(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    photo = await upload_photo(session, current_user, file)
    return success_response(PhotoPublic.model_validate(photo).model_dump(mode="json"))


@router.get("/{photo_id}/thumbnail")
async def photo_thumbnail_endpoint(
    photo_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> Response:
    file_asset, content = await decrypt_photo_variant(session, current_user, photo_id, "thumbnail")
    return Response(content=content, media_type=file_asset.mime_type or "image/jpeg")


@router.get("/{photo_id}/preview")
async def photo_preview_endpoint(
    photo_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> Response:
    file_asset, content = await decrypt_photo_variant(session, current_user, photo_id, "preview")
    return Response(content=content, media_type=file_asset.mime_type or "image/jpeg")


@router.get("/{photo_id}/original")
async def photo_original_endpoint(
    photo_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> Response:
    file_asset, content = await decrypt_photo_variant(session, current_user, photo_id, "original")
    return Response(content=content, media_type=file_asset.mime_type or "application/octet-stream")


@router.patch("/{photo_id}/favorite")
async def photo_favorite_endpoint(
    photo_id: UUID,
    is_favorite: bool,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    photo = await toggle_photo_favorite(session, current_user, photo_id, is_favorite)
    return success_response(PhotoPublic.model_validate(photo).model_dump(mode="json"))


@router.delete("/{photo_id}")
async def delete_photo_endpoint(
    photo_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    await delete_photo(session, current_user, photo_id)
    return success_response(None)
