from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FolderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    parent_id: UUID | None = None


class FolderUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    parent_id: UUID | None = None


class FolderPublic(BaseModel):
    id: UUID
    owner_id: UUID
    parent_id: UUID | None
    name: str
    path_cache: str | None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
