from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.schemas.document import DocumentCreateRequest


class VaultPinRequest(BaseModel):
    pin: str = Field(min_length=6, max_length=6)

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("PIN must be 6 digits")
        return value


class VaultStatus(BaseModel):
    pin_set: bool
    locked_until: str | None = None


class VaultUnlockResponse(BaseModel):
    unlock_token: str
    expires_in_seconds: int


class ImportantDocCreateRequest(BaseModel):
    title: str = Field(max_length=180)
    document_type: str = Field(default="other", max_length=80)
    issuer: str | None = Field(default=None, max_length=160)
    issued_date: date | None = None
    expires_at: date | None = None
    note: str | None = None

    def to_document_create(self) -> DocumentCreateRequest:
        return DocumentCreateRequest(
            title=self.title,
            document_type=self.document_type,
            issuer=self.issuer,
            issued_date=self.issued_date,
            expires_at=self.expires_at,
            note=self.note,
            security_level="vault_locked",
        )
