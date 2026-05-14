from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.invite import InvitePublic
from app.schemas.message import MessagePublic
from app.schemas.user import UserPublic


class AdminOverview(BaseModel):
    users_count: int
    active_users_count: int
    storage_bytes: int
    today_uploads_count: int
    error_count: int
    latest_backup: dict | None
    service_status: dict
    disk: dict


class AdminPlanPolicy(BaseModel):
    key: str
    name: str
    storage_limit_bytes: int | None
    max_public_shares: int | None
    max_share_downloads: int | None
    ocr_enabled: bool
    ai_enabled: bool


class AdminWorkerStatus(BaseModel):
    worker_tasks: dict
    ocr_tasks: dict
    document_intelligence_tasks: dict = {}
    backups: dict
    ai: dict = {}
    recent_failures: list[dict]


class AdminUserUpdateRequest(BaseModel):
    role: str | None = Field(default=None, max_length=32)
    plan: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=32)
    storage_limit_bytes: int | None = Field(default=None, ge=0)
    storage_limit_mb: int | None = Field(default=None, ge=0)


class AdminUserPublic(UserPublic):
    storage_used_bytes: int = 0


class AuditLogPublic(BaseModel):
    id: UUID
    actor_user_id: UUID | None
    action: str
    target_type: str | None
    target_id: str | None
    ip_address: str | None
    user_agent: str | None
    metadata_json: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BackupTaskPublic(BaseModel):
    id: UUID
    requested_by_user_id: UUID | None
    backup_type: str
    status: str
    backup_path: str | None
    file_size: int | None
    manifest_json: dict | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminBundle(BaseModel):
    overview: AdminOverview
    users: list[AdminUserPublic]
    invites: list[InvitePublic]
    audit_logs: list[AuditLogPublic]
    backups: list[BackupTaskPublic]
    messages: list[MessagePublic]
    plans: list[AdminPlanPolicy]
    worker: AdminWorkerStatus
    system_settings: dict = {}
