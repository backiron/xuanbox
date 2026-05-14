from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MessageCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=4000)
    level: str = Field(default="info", max_length=32)
    recipient_username: str | None = Field(default=None, max_length=255)


class MessagePublic(BaseModel):
    id: UUID
    sender_user_id: UUID | None
    recipient_user_id: UUID | None
    scope: str
    title: str
    body: str
    level: str
    read_at: datetime | None
    archived_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

