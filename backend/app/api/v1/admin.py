from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_admin
from app.core.responses import success_response
from app.models.user import User
from app.schemas.admin import AdminBundle, AdminUserUpdateRequest, AuditLogPublic, BackupTaskPublic
from app.schemas.invite import InvitePublic
from app.schemas.user import UserPublic
from app.services.admin_service import (
    admin_overview,
    list_admin_users,
    list_all_invites,
    list_audit_logs,
    list_backups,
    update_admin_user,
)
from app.services.backup_service import create_backup

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
    bundle = AdminBundle(
        overview=overview,
        users=[UserPublic.model_validate(user) for user in users],
        invites=[InvitePublic.model_validate(invite) for invite in invites],
        audit_logs=[AuditLogPublic.model_validate(log) for log in audit_logs],
        backups=[BackupTaskPublic.model_validate(backup) for backup in backups],
    )
    return success_response(bundle.model_dump(mode="json"))


@router.get("/overview")
async def admin_overview_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    return success_response((await admin_overview(session)).model_dump(mode="json"))


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


@router.get("/users")
async def admin_users_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    users = await list_admin_users(session)
    return success_response([UserPublic.model_validate(user).model_dump(mode="json") for user in users])


@router.patch("/users/{user_id}")
async def admin_update_user_endpoint(
    user_id: UUID,
    payload: AdminUserUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    user = await update_admin_user(session, current_user, user_id, payload)
    return success_response(UserPublic.model_validate(user).model_dump(mode="json"))


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
