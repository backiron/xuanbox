from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("amount", mode="before")
    @classmethod
    def normalize_amount(cls, value):
        if value in (None, ""):
            return None
        if isinstance(value, str):
            normalized = value.strip().replace(",", ".")
            normalized = "".join(char for char in normalized if char.isdigit() or char in ".-")
            if normalized in ("", "-", ".", "-."):
                return None
            return normalized
        return value

    @field_validator("purchase_date", "warranty_until", mode="before")
    @classmethod
    def normalize_date(cls, value):
        if value in (None, ""):
            return None
        if isinstance(value, str):
            normalized = value.strip().replace("/", "-").replace(".", "-")
            parts = normalized.split("-")
            if len(parts) == 3:
                year, month, day = parts if len(parts[0]) == 4 else (parts[2], parts[0], parts[1])
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        return value
