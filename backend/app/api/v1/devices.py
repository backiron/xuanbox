from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.core.responses import success_response
from app.models.device import Device
from app.models.user import User
from app.schemas.device import DevicePublic

router = APIRouter()


@router.get("")
async def list_devices(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await session.scalars(
        select(Device)
        .where(Device.owner_id == current_user.id)
        .order_by(Device.last_seen_at.desc().nullslast(), Device.created_at.desc())
    )
    return success_response(
        [DevicePublic.model_validate(device).model_dump(mode="json") for device in result]
    )
