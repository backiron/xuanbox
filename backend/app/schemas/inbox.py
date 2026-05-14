from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.file_asset import FileAssetPublic


class InboxResolveRequest(BaseModel):
    action: str = Field(pattern="^(photo|file|receipt|dismiss)$")


class InboxItemPublic(BaseModel):
    id: UUID
    owner_id: UUID
    file_id: UUID
    status: str
    source: str
    suggested_type: str | None
    suggestion_reason: str | None
    resolved_as: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    file: FileAssetPublic | None = None

    model_config = {"from_attributes": True}
