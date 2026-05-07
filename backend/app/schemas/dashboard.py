from datetime import date
from uuid import UUID

from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    storage_bytes: int
    photos_count: int
    files_count: int
    receipts_count: int
    documents_count: int
    pending_ocr_count: int


class ExpiringDocument(BaseModel):
    id: UUID
    title: str
    document_type: str
    issuer: str | None
    expires_at: date
    security_level: str


class DashboardSummary(BaseModel):
    metrics: DashboardMetrics
    expiring_documents: list[ExpiringDocument]
