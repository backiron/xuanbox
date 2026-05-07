from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def write_audit_log(
    session: AsyncSession,
    *,
    action: str,
    actor_user_id: UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    ip_address: str | None = None,
    device_id: UUID | None = None,
    user_agent: str | None = None,
    metadata_json: dict | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip_address=ip_address,
        device_id=device_id,
        user_agent=user_agent,
        metadata_json=metadata_json,
    )
    session.add(log)
    return log
