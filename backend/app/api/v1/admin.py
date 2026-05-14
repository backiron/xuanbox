from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_admin
from app.core.responses import success_response
from app.models.user import User
from app.schemas.admin import AdminBundle, AdminUserPublic, AdminUserUpdateRequest, AuditLogPublic, BackupTaskPublic
from app.schemas.invite import InvitePublic
from app.schemas.message import MessagePublic
from app.services.admin_service import (
    admin_overview,
    list_admin_users,
    list_all_invites,
    list_audit_logs,
    list_backups,
    update_admin_user,
    list_plan_policies,
    worker_status,
)
from app.services.backup_service import create_backup, delete_backup
from app.services.message_service import list_admin_messages
from app.services.system_settings_service import get_admin_system_settings, update_admin_system_settings

router = APIRouter()


@router.get("")
async def admin_bundle_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    overview = await admin_overview(session)
    users = await list_admin_users(session)
    invites = await list_all_invites(session)
    audit_logs = await list_audit_logs(session, limit=80)
    backups = await list_backups(session)
    messages = await list_admin_messages(session)
    plans = list_plan_policies()
    worker = await worker_status(session)
    system_settings = await get_admin_system_settings(session)
    bundle = AdminBundle(
        overview=overview,
        users=users,
        invites=[InvitePublic.model_validate(invite) for invite in invites],
        audit_logs=[AuditLogPublic.model_validate(log) for log in audit_logs],
        backups=[BackupTaskPublic.model_validate(backup) for backup in backups],
        messages=[MessagePublic.model_validate(message) for message in messages],
        plans=plans,
        worker=worker,
        system_settings=system_settings,
    )
    return success_response(bundle.model_dump(mode="json"))


@router.get("/overview")
async def admin_overview_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    return success_response((await admin_overview(session)).model_dump(mode="json"))


@router.get("/plans")
async def admin_plans_endpoint(
    current_user: User = Depends(require_admin),
) -> dict:
    return success_response([plan.model_dump(mode="json") for plan in list_plan_policies()])


@router.get("/worker")
async def admin_worker_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    return success_response((await worker_status(session)).model_dump(mode="json"))


@router.get("/health")
async def admin_health_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    overview = await admin_overview(session)
    return success_response(
        {
            "status": "ok",
            "services": overview.service_status,
            "disk": overview.disk,
            "latest_backup": overview.latest_backup,
        }
    )


@router.get("/system-settings")
async def admin_system_settings_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    return success_response(await get_admin_system_settings(session))


@router.patch("/system-settings")
async def admin_update_system_settings_endpoint(
    payload: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    settings = await update_admin_system_settings(
        session,
        current_user,
        registration_mode=payload.get("registration_mode"),
        default_free_storage_mb=payload.get("default_free_storage_mb"),
        auto_backup_enabled=payload.get("auto_backup_enabled"),
    )
    return success_response(settings)


@router.get("/users")
async def admin_users_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    users = await list_admin_users(session)
    return success_response([user.model_dump(mode="json") for user in users])


@router.patch("/users/{user_id}")
async def admin_update_user_endpoint(
    user_id: UUID,
    payload: AdminUserUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    user = await update_admin_user(session, current_user, user_id, payload)
    storage_used = await list_admin_users(session)
    updated = next((item for item in storage_used if item.id == user.id), None)
    return success_response((updated or AdminUserPublic.model_validate(user)).model_dump(mode="json"))


@router.get("/audit-logs")
async def admin_audit_logs_endpoint(
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    logs = await list_audit_logs(session, limit=limit)
    return success_response([AuditLogPublic.model_validate(log).model_dump(mode="json") for log in logs])


@router.get("/backups")
async def admin_backups_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    backups = await list_backups(session)
    return success_response([BackupTaskPublic.model_validate(backup).model_dump(mode="json") for backup in backups])


@router.post("/backups")
async def admin_create_backup_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    backup = await create_backup(session, current_user)
    return success_response(BackupTaskPublic.model_validate(backup).model_dump(mode="json"))


@router.delete("/backups/{backup_id}")
async def admin_delete_backup_endpoint(
    backup_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    await delete_backup(session, current_user, backup_id)
    return success_response({"deleted": True})
