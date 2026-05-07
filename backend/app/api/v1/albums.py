from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.core.responses import success_response
from app.models.user import User
from app.schemas.photo import AlbumCreateRequest, AlbumPublic, PhotoPublic
from app.services.album_service import add_photo_to_album, create_album, list_album_photos, list_albums

router = APIRouter()


@router.get("")
async def list_albums_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    albums = await list_albums(session, current_user)
    return success_response([AlbumPublic.model_validate(album).model_dump(mode="json") for album in albums])


@router.post("")
async def create_album_endpoint(
    payload: AlbumCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    album = await create_album(session, current_user, payload)
    return success_response(AlbumPublic.model_validate(album).model_dump(mode="json"))


@router.post("/{album_id}/photos/{photo_id}")
async def add_photo_endpoint(
    album_id: UUID,
    photo_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    await add_photo_to_album(session, current_user, album_id, photo_id)
    return success_response(message="added")


@router.get("/{album_id}/photos")
async def list_album_photos_endpoint(
    album_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    photos = await list_album_photos(session, current_user, album_id)
    return success_response([PhotoPublic.model_validate(photo).model_dump(mode="json") for photo in photos])
