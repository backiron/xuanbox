from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.services.audit_service import write_audit_log

REGISTRATION_INVITE_ONLY = "invite_only"
REGISTRATION_OPEN = "open"
REGISTRATION_CLOSED = "closed"
REGISTRATION_MODES = {REGISTRATION_INVITE_ONLY, REGISTRATION_OPEN, REGISTRATION_CLOSED}

SETTING_REGISTRATION_MODE = "registration_mode"
SETTING_DEFAULT_FREE_STORAGE_MB = "default_free_storage_mb"
DEFAULT_FREE_STORAGE_MB = 500


async def get_setting(db: AsyncSession, key: str, default: str) -> str:
    setting = await db.scalar(select(SystemSetting).where(SystemSetting.key == key))
    return setting.value if setting else default


async def set_setting(db: AsyncSession, key: str, value: str) -> SystemSetting:
    setting = await db.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if setting is None:
        setting = SystemSetting(key=key, value=value)
        db.add(setting)
    else:
        setting.value = value
    await db.flush()
    return setting


async def get_registration_mode(db: AsyncSession) -> str:
    mode = await get_setting(db, SETTING_REGISTRATION_MODE, REGISTRATION_INVITE_ONLY)
    return mode if mode in REGISTRATION_MODES else REGISTRATION_INVITE_ONLY


async def get_default_free_storage_mb(db: AsyncSession) -> int:
    raw_value = await get_setting(db, SETTING_DEFAULT_FREE_STORAGE_MB, str(DEFAULT_FREE_STORAGE_MB))
    try:
        value = int(raw_value)
    except ValueError:
        return DEFAULT_FREE_STORAGE_MB
    return max(0, value)


def mb_to_bytes(value: int) -> int:
    return value * 1024 * 1024


async def get_public_auth_settings(db: AsyncSession) -> dict:
    mode = await get_registration_mode(db)
    return {
        "registration_mode": mode,
        "open_registration_enabled": mode == REGISTRATION_OPEN,
        "invite_registration_enabled": mode in {REGISTRATION_INVITE_ONLY, REGISTRATION_OPEN},
    }


async def get_admin_system_settings(db: AsyncSession) -> dict:
    default_free_storage_mb = await get_default_free_storage_mb(db)
    return {
        **(await get_public_auth_settings(db)),
        "default_free_storage_mb": default_free_storage_mb,
        "default_free_storage_bytes": mb_to_bytes(default_free_storage_mb),
    }


async def update_admin_system_settings(
    db: AsyncSession,
    actor: User,
    *,
    registration_mode: str | None = None,
    default_free_storage_mb: int | None = None,
) -> dict:
    if registration_mode is not None:
        if registration_mode not in REGISTRATION_MODES:
            raise AppError("invalid_registration_mode", "Invalid registration mode", 400)
        await set_setting(db, SETTING_REGISTRATION_MODE, registration_mode)
    if default_free_storage_mb is not None:
        if default_free_storage_mb < 0:
            raise AppError("invalid_default_storage", "Default storage must be 0 MB or higher", 400)
        await set_setting(db, SETTING_DEFAULT_FREE_STORAGE_MB, str(default_free_storage_mb))
    await write_audit_log(db, action="admin.system_settings.update", actor_user_id=actor.id)
    await db.commit()
    return await get_admin_system_settings(db)
