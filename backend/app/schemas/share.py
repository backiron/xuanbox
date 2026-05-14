from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ShareCreateRequest(BaseModel):
    target_type: str = Field(max_length=32)
    target_id: UUID
    shared_with_username: str | None = Field(default=None, max_length=120)
    permission: str = Field(default="download", max_length=32)
    password: str | None = Field(default=None, min_length=1, max_length=120)
    max_downloads: int | None = Field(default=None, gt=0)
    expires_at: datetime | None = None


class ShareUpdateRequest(BaseModel):
    permission: str | None = Field(default=None, max_length=32)
    password: str | None = Field(default=None, max_length=120)
    max_downloads: int | None = Field(default=None, gt=0)
    expires_at: datetime | None = None
    is_active: bool | None = None


class SharePublic(BaseModel):
    id: UUID
    owner_id: UUID
    target_type: str
    target_id: UUID
    shared_with_user_id: UUID | None
    public_token: str
    permission: str
    max_downloads: int | None
    download_count: int
    expires_at: datetime | None
    is_active: bool
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    target_name: str | None = None
    requires_password: bool = False

    model_config = {"from_attributes": True}


class PublicShareMetadata(BaseModel):
    target_type: str
    target_name: str
    permission: str
    mime_type: str | None = None
    file_size: int | None = None
    max_downloads: int | None
    download_count: int
    expires_at: datetime | None
    requires_password: bool
    owner_name: str


class SharePasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=120)


class SharePasswordResponse(BaseModel):
    access_token: str
    expires_in_seconds: int
