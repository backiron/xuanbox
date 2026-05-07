from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PhotoPublic(BaseModel):
    id: UUID
    owner_id: UUID
    file_id: UUID
    taken_at: datetime | None
    uploaded_at: datetime
    width: int | None
    height: int | None
    camera_model: str | None
    orientation: int | None
    thumbnail_file_id: UUID | None
    preview_file_id: UUID | None
    is_favorite: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlbumCreateRequest(BaseModel):
    title: str
    description: str | None = None


class AlbumPublic(BaseModel):
    id: UUID
    owner_id: UUID
    title: str
    description: str | None
    cover_file_id: UUID | None
    visibility: str
    created_at: datetime

    model_config = {"from_attributes": True}
