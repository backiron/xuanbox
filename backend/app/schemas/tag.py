from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#1E3A5F", max_length=32)


class TagAttachRequest(BaseModel):
    target_type: str = Field(min_length=1, max_length=40)
    target_id: UUID


class TagPublic(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    color: str
    created_at: datetime

    model_config = {"from_attributes": True}
