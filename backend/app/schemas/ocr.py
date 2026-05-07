from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class OcrTaskPublic(BaseModel):
    id: UUID
    owner_id: UUID
    file_id: UUID
    receipt_id: UUID
    status: str
    raw_text: str | None
    parsed_json: dict | None
    error_message: str | None
    created_at: datetime
    finished_at: datetime | None
    confirmed_at: datetime | None

    model_config = {"from_attributes": True}


class OcrConfirmRequest(BaseModel):
    merchant: str | None = Field(default=None, max_length=160)
    category: str | None = Field(default=None, max_length=80)
    amount: Decimal | None = None
    currency: str | None = Field(default=None, max_length=8)
    purchase_date: date | None = None
    warranty_until: date | None = None
    notes: str | None = None
