from pydantic import BaseModel, EmailStr, Field


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None


class StorageUsagePublic(BaseModel):
    used_bytes: int
    limit_bytes: int | None
    remaining_bytes: int | None
    percent_used: int | None

