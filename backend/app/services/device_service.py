from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device


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
) -> Device:
    user_agent = request.headers.get("user-agent")
    client_host = request.client.host if request.client else None
    device = Device(
        owner_id=owner_id,
        device_name=device_name or infer_device_type(user_agent),
        device_type=infer_device_type(user_agent),
        os_name=None,
        browser_name=None,
        last_ip=client_host,
        last_seen_at=datetime.now(UTC),
    )
    session.add(device)
    await session.flush()
    return device
