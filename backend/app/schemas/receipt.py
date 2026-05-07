from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ReceiptCreateRequest(BaseModel):
    merchant: str | None = Field(default=None, max_length=160)
    category: str | None = Field(default=None, max_length=80)
    amount: Decimal | None = None
    currency: str = Field(default="USD", max_length=8)
    purchase_date: date | None = None
    warranty_until: date | None = None
    notes: str | None = None


class ReceiptUpdateRequest(ReceiptCreateRequest):
    pass


class ReceiptPublic(BaseModel):
    id: UUID
    owner_id: UUID
    file_id: UUID
    merchant: str | None
    category: str | None
    amount: Decimal | None
    currency: str
    purchase_date: date | None
    warranty_until: date | None
    notes: str | None
    ocr_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
