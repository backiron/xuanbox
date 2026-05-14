from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserPublic(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    display_name: str | None
    avatar_file_id: UUID | None
    role: str
    plan: str
    status: str
    storage_limit_bytes: int | None
    created_at: datetime
    last_login_at: datetime | None

    model_config = {"from_attributes": True}
