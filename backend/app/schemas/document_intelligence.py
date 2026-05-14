from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentIntelligenceTaskPublic(BaseModel):
    id: UUID
    owner_id: UUID
    file_id: UUID
    source_type: str
    status: str
    detected_type: str | None
    raw_text: str | None
    parsed_json: dict | None
    confidence: float | None
    error_message: str | None
    finished_at: datetime | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentProfilePublic(BaseModel):
    id: UUID
    owner_id: UUID
    file_id: UUID
    task_id: UUID | None
    title: str | None
    summary: str | None
    document_type: str
    issuer: str | None
    counterparty: str | None = None
    primary_date: str | None
    amount: str | None
    currency: str | None
    warranty_until: str | None
    serial_number: str | None
    keywords: list | None
    labels: list | None = None
    ai_summary: str | None = None
    ai_metadata: dict | None = None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentTextChunkPublic(BaseModel):
    id: UUID
    file_id: UUID
    task_id: UUID
    chunk_index: int
    page_number: int | None
    text: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentFieldValuePublic(BaseModel):
    id: UUID
    file_id: UUID
    profile_id: UUID
    field_key: str
    field_label: str | None
    field_value: str | None
    confidence: float | None
    source: str
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentProfileUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    summary: str | None = Field(default=None, max_length=4000)
    document_type: str | None = Field(default=None, max_length=64)
    issuer: str | None = Field(default=None, max_length=255)
    counterparty: str | None = Field(default=None, max_length=255)
    primary_date: str | None = Field(default=None, max_length=32)
    amount: str | None = Field(default=None, max_length=64)
    currency: str | None = Field(default=None, max_length=16)
    warranty_until: str | None = Field(default=None, max_length=32)
    serial_number: str | None = Field(default=None, max_length=120)
    keywords: list[str] | None = None
    labels: list[str] | None = None


class DocumentIntelligenceBundle(BaseModel):
    tasks: list[DocumentIntelligenceTaskPublic]
    profile: DocumentProfilePublic | None
    fields: list[DocumentFieldValuePublic] = []
    chunks: list[DocumentTextChunkPublic]
