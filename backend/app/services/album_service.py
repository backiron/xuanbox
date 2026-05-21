from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.album import Album, AlbumPhoto
from app.models.photo_asset import PhotoAsset
from app.models.user import User
from app.schemas.photo import AlbumCreateRequest, AlbumUpdateRequest
from app.services.audit_service import write_audit_log
from app.services.photo_service import delete_photo


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


async def update_album(db: AsyncSession, owner: User, album_id: UUID, payload: AlbumUpdateRequest) -> Album:
    album = await db.scalar(select(Album).where(Album.id == album_id, Album.owner_id == owner.id))
    if album is None:
        raise AppError("album_not_found", "Album not found", 404)
    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise AppError("album_title_required", "Album title is required", 422)
        album.title = title
    if payload.description is not None:
        album.description = payload.description
    await write_audit_log(db, action="album.update", actor_user_id=owner.id, target_type="album", target_id=str(album.id))
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


async def delete_album(db: AsyncSession, owner: User, album_id: UUID, delete_photos: bool = False) -> None:
    album = await db.scalar(select(Album).where(Album.id == album_id, Album.owner_id == owner.id))
    if album is None:
        raise AppError("album_not_found", "Album not found", 404)

    photo_ids = list(
        await db.scalars(
            select(AlbumPhoto.photo_id)
            .join(PhotoAsset, PhotoAsset.id == AlbumPhoto.photo_id)
            .where(AlbumPhoto.album_id == album_id, PhotoAsset.owner_id == owner.id)
        )
    )

    if delete_photos:
        for photo_id in photo_ids:
            await delete_photo(db, owner, photo_id)
        album = await db.scalar(select(Album).where(Album.id == album_id, Album.owner_id == owner.id))
        if album is None:
            return
    else:
        await db.execute(delete(AlbumPhoto).where(AlbumPhoto.album_id == album_id))

    await db.delete(album)
    await write_audit_log(
        db,
        action="album.delete",
        actor_user_id=owner.id,
        target_type="album",
        target_id=str(album_id),
        metadata_json={"delete_photos": delete_photos, "photo_count": len(photo_ids)},
    )
    await db.commit()
