from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FileAssetPublic(BaseModel):
    id: UUID
    owner_id: UUID
    folder_id: UUID | None
    original_filename: str
    display_name: str
    mime_type: str | None
    file_ext: str | None
    file_size: int
    sha256_hash: str
    file_category: str
    source: str
    is_favorite: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FileUpdateRequest(BaseModel):
    display_name: str | None = None
    folder_id: UUID | None = None
    is_favorite: bool | None = None
