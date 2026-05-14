from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.models.document_asset import DocumentAsset
from app.models.user import User
from app.schemas.document import DocumentCreateRequest
from app.services.audit_service import write_audit_log
from app.models.file_asset import FileAsset
from app.services.document_service import create_document_for_file, get_owned_document
from app.services.file_service import decrypt_file_asset, get_owned_file

VAULT_UNLOCK_SECONDS = 10 * 60
MAX_PIN_ATTEMPTS = 5
PIN_LOCK_MINUTES = 15


def _now() -> datetime:
    return datetime.now(UTC)


def _pin_locked_until(owner: User) -> datetime | None:
    locked_until = owner.vault_pin_locked_until
    if locked_until and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=UTC)
    if locked_until and locked_until > _now():
        return locked_until
    return None


async def setup_vault_pin(db: AsyncSession, owner: User, pin: str) -> str:
    if owner.vault_pin_hash:
        raise AppError("vault_pin_exists", "Important docs PIN is already set", 409)
    owner.vault_pin_hash = hash_password(pin)
    owner.vault_pin_failed_attempts = 0
    owner.vault_pin_locked_until = None
    await write_audit_log(db, action="important_docs.pin_setup", actor_user_id=owner.id)
    await db.commit()
    return create_vault_unlock_token(owner)


async def unlock_vault_pin(db: AsyncSession, owner: User, pin: str) -> str:
    if not owner.vault_pin_hash:
        raise AppError("vault_pin_not_set", "Set an Important docs PIN first", 400)
    locked_until = _pin_locked_until(owner)
    if locked_until:
        raise AppError("vault_pin_locked", "Too many incorrect PIN attempts. Try again later.", 423)
    if not verify_password(pin, owner.vault_pin_hash):
        owner.vault_pin_failed_attempts += 1
        if owner.vault_pin_failed_attempts >= MAX_PIN_ATTEMPTS:
            owner.vault_pin_locked_until = _now() + timedelta(minutes=PIN_LOCK_MINUTES)
        await write_audit_log(db, action="important_docs.pin_failed", actor_user_id=owner.id)
        await db.commit()
        raise AppError("invalid_vault_pin", "Incorrect PIN", 403)
    owner.vault_pin_failed_attempts = 0
    owner.vault_pin_locked_until = None
    await write_audit_log(db, action="important_docs.pin_unlock", actor_user_id=owner.id)
    await db.commit()
    return create_vault_unlock_token(owner)


def create_vault_unlock_token(owner: User) -> str:
    return create_access_token(
        str(owner.id),
        {
            "type": "vault_unlock",
            "scope": "important_docs",
            "exp": int((_now() + timedelta(seconds=VAULT_UNLOCK_SECONDS)).timestamp()),
        },
    )


def verify_vault_unlock_token(owner: User, token: str | None) -> None:
    if not owner.vault_pin_hash:
        raise AppError("vault_pin_not_set", "Set an Important docs PIN first", 400)
    if not token:
        raise AppError("vault_unlock_required", "Unlock Important docs first", 401)
    payload = decode_token(token)
    if payload.get("type") != "vault_unlock" or payload.get("scope") != "important_docs" or payload.get("sub") != str(owner.id):
        raise AppError("invalid_vault_unlock", "Invalid Important docs unlock token", 401)


async def list_important_docs(db: AsyncSession, owner: User) -> list[DocumentAsset]:
    from sqlalchemy import select

    result = await db.scalars(
        select(DocumentAsset)
        .where(DocumentAsset.owner_id == owner.id, DocumentAsset.security_level == "vault_locked")
        .order_by(DocumentAsset.expires_at.asc().nullslast(), DocumentAsset.updated_at.desc())
    )
    return list(result)


async def create_important_doc_for_file(
    db: AsyncSession,
    owner: User,
    file_id: UUID,
    payload: DocumentCreateRequest,
) -> DocumentAsset:
    document = await create_document_for_file(db, owner, file_id, payload, allow_vault_locked=True)
    await write_audit_log(db, action="important_docs.add_file", actor_user_id=owner.id)
    await db.commit()
    return document


async def decrypt_important_doc(db: AsyncSession, owner: User, document_id: UUID) -> tuple[DocumentAsset, FileAsset, bytes]:
    document = await get_owned_document(db, owner, document_id)
    if document.security_level != "vault_locked":
        raise AppError("important_doc_not_found", "Important doc not found", 404)
    file_asset = await get_owned_file(db, owner, document.file_id, allow_vault_locked=True)
    document.last_viewed_at = _now()
    plain_bytes = decrypt_file_asset(file_asset)
    await write_audit_log(db, action="important_docs.download", actor_user_id=owner.id, target_id=str(document.id), target_type="document")
    await db.commit()
    return document, file_asset, plain_bytes


async def remove_important_doc(db: AsyncSession, owner: User, document_id: UUID) -> None:
    document = await get_owned_document(db, owner, document_id)
    if document.security_level != "vault_locked":
        raise AppError("important_doc_not_found", "Important doc not found", 404)
    await write_audit_log(db, action="important_docs.remove", actor_user_id=owner.id, target_id=str(document.id), target_type="document")
    await db.delete(document)
    await db.commit()
