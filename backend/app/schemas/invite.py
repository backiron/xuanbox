from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class InviteCreateRequest(BaseModel):
    role_to_assign: str = "user"
    max_uses: int = Field(default=1, ge=1, le=100)
    expires_at: datetime | None = None
    note: str | None = Field(default=None, max_length=500)


class InvitePublic(BaseModel):
    id: UUID
    invite_code: str
    created_by_user_id: UUID
    role_to_assign: str
    max_uses: int
    used_count: int
    expires_at: datetime | None
    is_active: bool
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
