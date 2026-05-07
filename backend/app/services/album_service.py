from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.album import Album, AlbumPhoto
from app.models.photo_asset import PhotoAsset
from app.models.user import User
from app.schemas.photo import AlbumCreateRequest
from app.services.audit_service import write_audit_log


async def list_albums(db: AsyncSession, owner: User) -> list[Album]:
    result = await db.scalars(select(Album).where(Album.owner_id == owner.id).order_by(Album.updated_at.desc()))
    return list(result)


async def list_album_photos(db: AsyncSession, owner: User, album_id: UUID) -> list[PhotoAsset]:
    album = await db.scalar(select(Album).where(Album.id == album_id, Album.owner_id == owner.id))
    if album is None:
        raise AppError("album_not_found", "Album not found", 404)
    result = await db.scalars(
        select(PhotoAsset)
        .join(AlbumPhoto, AlbumPhoto.photo_id == PhotoAsset.id)
        .where(AlbumPhoto.album_id == album_id, PhotoAsset.owner_id == owner.id)
        .order_by(AlbumPhoto.sort_order.asc(), PhotoAsset.uploaded_at.desc())
    )
    return list(result)


async def create_album(db: AsyncSession, owner: User, payload: AlbumCreateRequest) -> Album:
    album = Album(owner_id=owner.id, title=payload.title, description=payload.description)
    db.add(album)
    await db.flush()
    await write_audit_log(db, action="album.create", actor_user_id=owner.id, target_type="album", target_id=str(album.id))
    await db.commit()
    await db.refresh(album)
    return album


async def add_photo_to_album(db: AsyncSession, owner: User, album_id: UUID, photo_id: UUID) -> None:
    album = await db.scalar(select(Album).where(Album.id == album_id, Album.owner_id == owner.id))
    photo = await db.scalar(select(PhotoAsset).where(PhotoAsset.id == photo_id, PhotoAsset.owner_id == owner.id))
    if album is None:
        raise AppError("album_not_found", "Album not found", 404)
    if photo is None:
        raise AppError("photo_not_found", "Photo not found", 404)
    existing = await db.scalar(select(AlbumPhoto).where(AlbumPhoto.album_id == album_id, AlbumPhoto.photo_id == photo_id))
    if existing is None:
        db.add(AlbumPhoto(album_id=album_id, photo_id=photo_id))
    if album.cover_file_id is None:
        album.cover_file_id = photo.file_id
    await write_audit_log(db, action="album.add_photo", actor_user_id=owner.id, target_type="album", target_id=str(album_id))
    await db.commit()
