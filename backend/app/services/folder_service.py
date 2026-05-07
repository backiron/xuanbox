from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.folder import Folder
from app.models.user import User
from app.schemas.folder import FolderCreateRequest, FolderUpdateRequest
from app.services.audit_service import write_audit_log


async def get_owned_folder(db: AsyncSession, owner: User, folder_id: UUID, allow_deleted: bool = False) -> Folder:
    folder = await db.scalar(select(Folder).where(Folder.id == folder_id, Folder.owner_id == owner.id))
    if folder is None or (folder.is_deleted and not allow_deleted):
        raise AppError("folder_not_found", "Folder not found", 404)
    return folder


async def list_folders(db: AsyncSession, owner: User, parent_id: UUID | None = None) -> list[Folder]:
    statement = select(Folder).where(Folder.owner_id == owner.id, Folder.is_deleted.is_(False))
    if parent_id is None:
        statement = statement.where(Folder.parent_id.is_(None))
    else:
        statement = statement.where(Folder.parent_id == parent_id)
    result = await db.scalars(statement.order_by(Folder.name.asc()))
    return list(result)


async def create_folder(db: AsyncSession, owner: User, payload: FolderCreateRequest) -> Folder:
    if payload.parent_id is not None:
        await get_owned_folder(db, owner, payload.parent_id)
    folder = Folder(owner_id=owner.id, parent_id=payload.parent_id, name=payload.name, path_cache=payload.name)
    db.add(folder)
    await db.flush()
    await write_audit_log(db, action="folder.create", actor_user_id=owner.id, target_type="folder", target_id=str(folder.id))
    await db.commit()
    await db.refresh(folder)
    return folder


async def update_folder(db: AsyncSession, owner: User, folder_id: UUID, payload: FolderUpdateRequest) -> Folder:
    folder = await get_owned_folder(db, owner, folder_id)
    if payload.parent_id is not None:
        await get_owned_folder(db, owner, payload.parent_id)
    if payload.name is not None:
        folder.name = payload.name
        folder.path_cache = payload.name
    if payload.parent_id is not None:
        folder.parent_id = payload.parent_id
    await write_audit_log(db, action="folder.update", actor_user_id=owner.id, target_type="folder", target_id=str(folder.id))
    await db.commit()
    await db.refresh(folder)
    return folder


async def delete_folder(db: AsyncSession, owner: User, folder_id: UUID) -> None:
    folder = await get_owned_folder(db, owner, folder_id)
    folder.is_deleted = True
    folder.deleted_at = datetime.now(UTC)
    await write_audit_log(db, action="folder.delete", actor_user_id=owner.id, target_type="folder", target_id=str(folder.id))
    await db.commit()
