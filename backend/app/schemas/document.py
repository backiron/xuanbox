from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentCreateRequest(BaseModel):
    document_type: str = Field(default="contract", max_length=80)
    title: str = Field(max_length=180)
    issuer: str | None = Field(default=None, max_length=160)
    issued_date: date | None = None
    expires_at: date | None = None
    note: str | None = None
    security_level: str = Field(default="normal", max_length=32)


class DocumentUpdateRequest(BaseModel):
    document_type: str | None = Field(default=None, max_length=80)
    title: str | None = Field(default=None, max_length=180)
    issuer: str | None = Field(default=None, max_length=160)
    issued_date: date | None = None
    expires_at: date | None = None
    note: str | None = None
    security_level: str | None = Field(default=None, max_length=32)


class DocumentPublic(BaseModel):
    id: UUID
    owner_id: UUID
    file_id: UUID
    document_type: str
    title: str
    issuer: str | None
    issued_date: date | None
    expires_at: date | None
    note: str | None
    security_level: str
    last_viewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
