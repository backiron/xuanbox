from uuid import UUID

from pydantic import BaseModel, Field


class DropTextMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=20000)
    target_device_id: UUID | None = None
    client_id: str | None = Field(default=None, max_length=64)


class DropSaveRequest(BaseModel):
    destination: str = Field(pattern="^(files|photos|receipts)$")
    merchant: str | None = Field(default=None, max_length=160)
    category: str | None = Field(default=None, max_length=80)


class DropContactRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)


class DropDirectThreadRequest(BaseModel):
    user_id: UUID


class DropDeviceRenameRequest(BaseModel):
    device_name: str = Field(min_length=1, max_length=120)


class DropUploadStartRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str | None = Field(default=None, max_length=160)
    file_size: int = Field(gt=0)
    target_device_id: UUID | None = None
    client_id: str | None = Field(default=None, max_length=64)
