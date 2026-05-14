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
from app.models.document_intelligence import DocumentIntelligenceTask
from app.models.file_asset import FileAsset
from app.models.invite import Invite
from app.models.ocr_task import OcrTask
from app.models.user import User
from app.models.worker_task import WorkerTask
from app.schemas.admin import AdminOverview, AdminPlanPolicy, AdminUserPublic, AdminUserUpdateRequest, AdminWorkerStatus
from app.services.audit_service import write_audit_log
from app.services.system_settings_service import mb_to_bytes

VALID_ROLES = {"owner", "admin", "user", "guest"}
VALID_PLANS = {"free", "pro"}
VALID_STATUSES = {"active", "disabled"}

PLAN_POLICIES = [
    AdminPlanPolicy(key="free", name="Free", storage_limit_bytes=500 * 1024**2, max_public_shares=5, max_share_downloads=3, ocr_enabled=True, ai_enabled=False),
    AdminPlanPolicy(key="pro", name="Pro", storage_limit_bytes=50 * 1024**3, max_public_shares=500, max_share_downloads=100, ocr_enabled=True, ai_enabled=True),
]


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


async def list_admin_users(db: AsyncSession) -> list[AdminUserPublic]:
    result = await db.execute(
        select(User, func.coalesce(func.sum(FileAsset.file_size), 0).label("storage_used_bytes"))
        .outerjoin(
            FileAsset,
            (FileAsset.owner_id == User.id) & (FileAsset.is_deleted.is_(False)),
        )
        .group_by(User.id)
        .order_by(User.created_at.desc())
    )
    users: list[AdminUserPublic] = []
    for user, storage_used_bytes in result.all():
        data = AdminUserPublic.model_validate(user).model_dump()
        data["storage_used_bytes"] = int(storage_used_bytes or 0)
        users.append(AdminUserPublic(**data))
    return users


async def update_admin_user(db: AsyncSession, actor: User, user_id: UUID, payload: AdminUserUpdateRequest) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise AppError("user_not_found", "User not found", 404)
    if payload.role is not None:
        if payload.role not in VALID_ROLES:
            raise AppError("invalid_role", "Invalid role", 400)
        user.role = payload.role
    if payload.plan is not None:
        if payload.plan not in VALID_PLANS:
            raise AppError("invalid_plan", "Invalid plan", 400)
        user.plan = payload.plan
    if payload.status is not None:
        if payload.status not in VALID_STATUSES:
            raise AppError("invalid_status", "Invalid status", 400)
        if user.id == actor.id and payload.status != "active":
            raise AppError("cannot_disable_self", "You cannot disable your own account", 400)
        user.status = payload.status
    if "storage_limit_mb" in payload.model_fields_set:
        user.storage_limit_bytes = None if payload.storage_limit_mb is None else mb_to_bytes(payload.storage_limit_mb)
    elif "storage_limit_bytes" in payload.model_fields_set:
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


def list_plan_policies() -> list[AdminPlanPolicy]:
    return PLAN_POLICIES


async def worker_status(db: AsyncSession) -> AdminWorkerStatus:
    worker_rows = await db.execute(select(WorkerTask.status, func.count(WorkerTask.id)).group_by(WorkerTask.status))
    ocr_rows = await db.execute(select(OcrTask.status, func.count(OcrTask.id)).group_by(OcrTask.status))
    intelligence_rows = await db.execute(select(DocumentIntelligenceTask.status, func.count(DocumentIntelligenceTask.id)).group_by(DocumentIntelligenceTask.status))
    backup_rows = await db.execute(select(BackupTask.status, func.count(BackupTask.id)).group_by(BackupTask.status))
    failures = await db.scalars(
        select(WorkerTask)
        .where(WorkerTask.status == "failed")
        .order_by(WorkerTask.finished_at.desc().nullslast(), WorkerTask.created_at.desc())
        .limit(10)
    )
    return AdminWorkerStatus(
        worker_tasks={status: int(count) for status, count in worker_rows.all()},
        ocr_tasks={status: int(count) for status, count in ocr_rows.all()},
        document_intelligence_tasks={status: int(count) for status, count in intelligence_rows.all()},
        backups={status: int(count) for status, count in backup_rows.all()},
        ai={
            "enabled": settings.DOCUMENT_AI_ENABLED,
            "model": settings.DOCUMENT_AI_MODEL,
            "base_url": settings.DOCUMENT_AI_BASE_URL,
            "timeout_seconds": settings.DOCUMENT_AI_TIMEOUT_SECONDS,
            "max_chars": settings.DOCUMENT_AI_MAX_CHARS,
            "concurrency": settings.DOCUMENT_AI_CONCURRENCY,
        },
        recent_failures=[
            {
                "id": str(task.id),
                "task_type": task.task_type,
                "target_type": task.target_type,
                "status": task.status,
                "attempts": task.attempts,
                "error_message": task.error_message,
                "finished_at": task.finished_at.isoformat() if task.finished_at else None,
            }
            for task in failures
        ],
    )


def backup_directory() -> Path:
    path = Path(settings.STORAGE_ROOT) / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path
