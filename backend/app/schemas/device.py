from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DevicePublic(BaseModel):
    id: UUID
    owner_id: UUID
    device_name: str
    device_type: str
    os_name: str | None
    browser_name: str | None
    last_ip: str | None
    last_seen_at: datetime | None
    is_trusted: bool
    revoked_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
