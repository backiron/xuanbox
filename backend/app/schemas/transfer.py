from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TransferSessionCreateRequest(BaseModel):
    title: str = Field(default="XuanDrop", min_length=1, max_length=160)
    expires_in_minutes: int = Field(default=5, ge=1, le=120)


class TransferSessionPublic(BaseModel):
    id: UUID
    owner_id: UUID
    title: str
    status: str
    expires_at: datetime
    created_at: datetime
    upload_url: str | None = None
    token: str | None = None

    model_config = {"from_attributes": True}


class TransferItemPublic(BaseModel):
    id: UUID
    session_id: UUID
    owner_id: UUID
    file_id: UUID
    original_filename: str
    mime_type: str | None
    file_size: int
    status: str
    saved_to: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransferSaveRequest(BaseModel):
    destination: str = Field(pattern="^(files|photos|receipts)$")
    merchant: str | None = Field(default=None, max_length=160)
    category: str | None = Field(default=None, max_length=80)
