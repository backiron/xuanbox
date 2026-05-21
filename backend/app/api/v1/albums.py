from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.responses import success_response
from app.models.user import User
from app.schemas.photo import AlbumCreateRequest, AlbumPublic, AlbumUpdateRequest, PhotoPublic
from app.services.album_service import add_photo_to_album, create_album, delete_album, list_album_photos, list_albums, update_album

router = APIRouter()


@router.get("")
async def list_albums_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    albums = await list_albums(session, current_user)
    return success_response([AlbumPublic.model_validate(album).model_dump(mode="json") for album in albums])


@router.post("")
async def create_album_endpoint(
    payload: AlbumCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    album = await create_album(session, current_user, payload)
    return success_response(AlbumPublic.model_validate(album).model_dump(mode="json"))


@router.patch("/{album_id}")
async def update_album_endpoint(
    album_id: UUID,
    payload: AlbumUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    album = await update_album(session, current_user, album_id, payload)
    return success_response(AlbumPublic.model_validate(album).model_dump(mode="json"))


@router.post("/{album_id}/photos/{photo_id}")
async def add_photo_endpoint(
    album_id: UUID,
    photo_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    await add_photo_to_album(session, current_user, album_id, photo_id)
    return success_response(message="added")


@router.delete("/{album_id}")
async def delete_album_endpoint(
    album_id: UUID,
    delete_photos: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    await delete_album(session, current_user, album_id, delete_photos=delete_photos)
    return success_response(None)


@router.get("/{album_id}/photos")
async def list_album_photos_endpoint(
    album_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    photos = await list_album_photos(session, current_user, album_id)
    return success_response([PhotoPublic.model_validate(photo).model_dump(mode="json") for photo in photos])
