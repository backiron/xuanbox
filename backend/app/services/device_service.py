from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import client_ip
from app.core.security import hash_token
from app.models.device import Device

# Names older clients sent for every device; a better name from the client replaces them.
GENERIC_DEVICE_NAMES = {"Local Browser", "Browser", "Unknown Device"}


def infer_device_type(user_agent: str | None) -> str:
    if not user_agent:
        return "Unknown Device"
    ua = user_agent.lower()
    if "iphone" in ua:
        return "iPhone"
    if "ipad" in ua:
        return "iPad"
    if "android" in ua and "mobile" in ua:
        return "Android Phone"
    if "android" in ua:
        return "Android Tablet"
    if "macintosh" in ua or "mac os" in ua:
        return "Mac"
    if "windows" in ua:
        return "Windows PC"
    return "Browser"


async def create_login_device(
    session: AsyncSession,
    *,
    owner_id: UUID,
    request: Request,
    device_name: str | None = None,
    device_key: str | None = None,
) -> Device:
    user_agent = request.headers.get("user-agent")
    client_host = client_ip(request)
    client_key_hash = hash_token(device_key) if device_key else None
    if client_key_hash:
        existing = await session.scalar(
            select(Device)
            .where(Device.owner_id == owner_id, Device.client_key_hash == client_key_hash, Device.revoked_at.is_(None))
            .order_by(Device.created_at.desc())
            .limit(1)
        )
        if existing is not None:
            if device_name and existing.device_name in GENERIC_DEVICE_NAMES:
                existing.device_name = device_name
            existing.last_ip = client_host
            existing.last_seen_at = datetime.now(UTC)
            return existing
    device = Device(
        owner_id=owner_id,
        device_name=device_name or infer_device_type(user_agent),
        device_type=infer_device_type(user_agent),
        os_name=None,
        browser_name=None,
        last_ip=client_host,
        last_seen_at=datetime.now(UTC),
        client_key_hash=client_key_hash,
    )
    session.add(device)
    await session.flush()
    return device
