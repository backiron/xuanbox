import shutil
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.models.audit_log import AuditLog
from app.models.backup_task import BackupTask
from app.models.file_asset import FileAsset
from app.models.invite import Invite
from app.models.user import User
from app.schemas.admin import AdminOverview, AdminUserUpdateRequest
from app.services.audit_service import write_audit_log

VALID_ROLES = {"owner", "admin", "user", "guest"}
VALID_STATUSES = {"active", "disabled"}


async def admin_overview(db: AsyncSession) -> AdminOverview:
    today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=UTC)
    users_count = await db.scalar(select(func.count(User.id)))
    active_users_count = await db.scalar(select(func.count(User.id)).where(User.status == "active"))
    storage_bytes = await db.scalar(select(func.coalesce(func.sum(FileAsset.file_size), 0)).where(FileAsset.is_deleted.is_(False)))
    today_uploads_count = await db.scalar(select(func.count(FileAsset.id)).where(FileAsset.created_at >= today_start))
    error_count = await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action.ilike("%error%")))
    latest_backup = await db.scalar(select(BackupTask).order_by(BackupTask.created_at.desc()).limit(1))
    usage = shutil.disk_usage(settings.STORAGE_ROOT)
    return AdminOverview(
        users_count=int(users_count or 0),
        active_users_count=int(active_users_count or 0),
        storage_bytes=int(storage_bytes or 0),
        today_uploads_count=int(today_uploads_count or 0),
        error_count=int(error_count or 0),
        latest_backup={
            "id": str(latest_backup.id),
            "status": latest_backup.status,
            "created_at": latest_backup.created_at.isoformat(),
            "file_size": latest_backup.file_size,
        }
        if latest_backup
        else None,
        service_status={"api": "ok", "database": "ok", "redis": "ok"},
        disk={"total": usage.total, "used": usage.used, "free": usage.free},
    )


async def list_admin_users(db: AsyncSession) -> list[User]:
    result = await db.scalars(select(User).order_by(User.created_at.desc()))
    return list(result)


async def update_admin_user(db: AsyncSession, actor: User, user_id: UUID, payload: AdminUserUpdateRequest) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise AppError("user_not_found", "User not found", 404)
    if payload.role is not None:
        if payload.role not in VALID_ROLES:
            raise AppError("invalid_role", "Invalid role", 400)
        user.role = payload.role
    if payload.status is not None:
        if payload.status not in VALID_STATUSES:
            raise AppError("invalid_status", "Invalid status", 400)
        if user.id == actor.id and payload.status != "active":
            raise AppError("cannot_disable_self", "You cannot disable your own account", 400)
        user.status = payload.status
    if "storage_limit_bytes" in payload.model_fields_set:
        user.storage_limit_bytes = payload.storage_limit_bytes
    await write_audit_log(db, action="admin.user.update", actor_user_id=actor.id, target_type="user", target_id=str(user.id))
    await db.commit()
    await db.refresh(user)
    return user


async def list_audit_logs(db: AsyncSession, *, limit: int = 100) -> list[AuditLog]:
    result = await db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 500)))
    return list(result)


async def list_all_invites(db: AsyncSession) -> list[Invite]:
    result = await db.scalars(select(Invite).order_by(Invite.created_at.desc()))
    return list(result)


async def list_backups(db: AsyncSession) -> list[BackupTask]:
    result = await db.scalars(select(BackupTask).order_by(BackupTask.created_at.desc()).limit(50))
    return list(result)


def backup_directory() -> Path:
    path = Path(settings.STORAGE_ROOT) / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path
