from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import verify_password
from app.models.document_asset import DocumentAsset
from app.models.file_asset import FileAsset
from app.models.user import User
from app.schemas.document import DocumentCreateRequest, DocumentUpdateRequest
from app.services.file_service import decrypt_file_asset, get_owned_file, upload_file

ALLOWED_DOCUMENT_TYPES = {
    "identity",
    "passport",
    "driver_license",
    "visa",
    "pr_card",
    "insurance",
    "tax",
    "bank",
    "contract",
    "home",
    "vehicle",
    "medical",
    "school",
    "software_license",
    "other",
}
ALLOWED_SECURITY_LEVELS = {"normal", "sensitive", "high_sensitive", "vault_locked"}
SECOND_FACTOR_LEVELS = {"high_sensitive", "vault_locked"}


def _validate_document_type(value: str) -> str:
    normalized = value.lower()
    if normalized not in ALLOWED_DOCUMENT_TYPES:
        raise AppError("invalid_document_type", "Unsupported document type", 400)
    return normalized


def _validate_security_level(value: str) -> str:
    normalized = value.lower()
    if normalized not in ALLOWED_SECURITY_LEVELS:
        raise AppError("invalid_security_level", "Unsupported security level", 400)
    return normalized


async def list_documents(
    db: AsyncSession,
    owner: User,
    *,
    q: str | None = None,
    document_type: str | None = None,
    security_level: str | None = None,
) -> list[DocumentAsset]:
    statement = select(DocumentAsset).where(DocumentAsset.owner_id == owner.id)
    if q:
        like = f"%{q}%"
        statement = statement.where(DocumentAsset.title.ilike(like) | DocumentAsset.issuer.ilike(like) | DocumentAsset.note.ilike(like))
    if document_type:
        statement = statement.where(DocumentAsset.document_type == document_type)
    if security_level:
        statement = statement.where(DocumentAsset.security_level == security_level)
    result = await db.scalars(statement.order_by(DocumentAsset.expires_at.asc().nullslast(), DocumentAsset.updated_at.desc()))
    return list(result)


async def create_document_from_upload(
    db: AsyncSession,
    owner: User,
    upload: UploadFile,
    payload: DocumentCreateRequest,
) -> DocumentAsset:
    file_asset = await upload_file(db, owner=owner, upload=upload, source="document_upload")
    file_asset.file_category = "document"
    document = DocumentAsset(
        owner_id=owner.id,
        file_id=file_asset.id,
        document_type=_validate_document_type(payload.document_type),
        title=payload.title,
        issuer=payload.issuer,
        issued_date=payload.issued_date,
        expires_at=payload.expires_at,
        note=payload.note,
        security_level=_validate_security_level(payload.security_level),
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


async def create_document_for_file(
    db: AsyncSession,
    owner: User,
    file_id: UUID,
    payload: DocumentCreateRequest,
) -> DocumentAsset:
    await get_owned_file(db, owner, file_id)
    existing = await db.scalar(select(DocumentAsset).where(DocumentAsset.file_id == file_id, DocumentAsset.owner_id == owner.id))
    if existing:
        raise AppError("document_exists", "This file is already saved as a document", 409)
    document = DocumentAsset(
        owner_id=owner.id,
        file_id=file_id,
        document_type=_validate_document_type(payload.document_type),
        title=payload.title,
        issuer=payload.issuer,
        issued_date=payload.issued_date,
        expires_at=payload.expires_at,
        note=payload.note,
        security_level=_validate_security_level(payload.security_level),
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


async def get_owned_document(db: AsyncSession, owner: User, document_id: UUID) -> DocumentAsset:
    document = await db.scalar(select(DocumentAsset).where(DocumentAsset.id == document_id, DocumentAsset.owner_id == owner.id))
    if document is None:
        raise AppError("document_not_found", "Document not found", 404)
    return document


async def update_document(db: AsyncSession, owner: User, document_id: UUID, payload: DocumentUpdateRequest) -> DocumentAsset:
    document = await get_owned_document(db, owner, document_id)
    if payload.document_type is not None:
        document.document_type = _validate_document_type(payload.document_type)
    if payload.title is not None:
        document.title = payload.title
    if "issuer" in payload.model_fields_set:
        document.issuer = payload.issuer
    if "issued_date" in payload.model_fields_set:
        document.issued_date = payload.issued_date
    if "expires_at" in payload.model_fields_set:
        document.expires_at = payload.expires_at
    if "note" in payload.model_fields_set:
        document.note = payload.note
    if payload.security_level is not None:
        document.security_level = _validate_security_level(payload.security_level)
    await db.commit()
    await db.refresh(document)
    return document


async def decrypt_document(
    db: AsyncSession,
    owner: User,
    document_id: UUID,
    *,
    password: str | None = None,
) -> tuple[DocumentAsset, FileAsset, bytes]:
    document = await get_owned_document(db, owner, document_id)
    if document.security_level in SECOND_FACTOR_LEVELS and not verify_password(password or "", owner.password_hash):
        raise AppError("document_reauth_required", "Password verification required for this document", 403)
    file_asset = await get_owned_file(db, owner, document.file_id)
    document.last_viewed_at = datetime.now(UTC)
    plain_bytes = decrypt_file_asset(file_asset)
    await db.commit()
    return document, file_asset, plain_bytes


async def list_expiring_documents(db: AsyncSession, owner: User, *, days: int = 90) -> list[DocumentAsset]:
    today = date.today()
    until = today + timedelta(days=days)
    result = await db.scalars(
        select(DocumentAsset)
        .where(DocumentAsset.owner_id == owner.id, DocumentAsset.expires_at.is_not(None))
        .where(DocumentAsset.expires_at >= today, DocumentAsset.expires_at <= until)
        .order_by(DocumentAsset.expires_at.asc())
    )
    return list(result)
