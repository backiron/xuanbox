"""Online Markdown editing (Pro only): .md files live in the normal encrypted file library.

Saving rewrites the encrypted blob under a fresh key and refreshes the keyword-search text
inline. No AI and no embeddings run on save, so frequent autosaves stay cheap.
"""

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.document_intelligence import DocumentIntelligenceTask, DocumentTextChunk
from app.models.file_asset import FileAsset
from app.models.folder import Folder
from app.models.user import User
from app.services.audit_service import write_audit_log
from app.services.document_intelligence_service import chunk_text
from app.services.encryption_service import encrypt_bytes, generate_file_key, wrap_file_key
from app.services.file_service import create_encrypted_asset_from_bytes, decrypt_file_asset, ensure_storage_quota, get_owned_file
from app.services.storage_service import delete_physical_file, encrypted_file_path, save_encrypted_file

MARKDOWN_EXTENSIONS = {"md", "markdown"}
MARKDOWN_MIME = "text/markdown"
MAX_MARKDOWN_BYTES = 2 * 1024 * 1024
SOURCE = "markdown_editor"


def require_pro(user: User) -> None:
    if user.plan != "pro":
        raise AppError("markdown_pro_only", "Online Markdown editing is a Pro feature", 403)


def is_markdown_file(file_asset: FileAsset) -> bool:
    return (file_asset.file_ext or "").lower() in MARKDOWN_EXTENSIONS


def _encode(content: str) -> bytes:
    data = content.encode("utf-8")
    if len(data) > MAX_MARKDOWN_BYTES:
        raise AppError("markdown_too_large", "Markdown documents can be at most 2 MB", 413)
    return data


def _filename(name: str) -> str:
    name = " ".join((name or "").replace("/", " ").replace("\\", " ").split()).strip()
    if not name:
        raise AppError("markdown_name_required", "Give the document a name", 400)
    if Path(name).suffix.lower().lstrip(".") not in MARKDOWN_EXTENSIONS:
        name = f"{name}.md"
    if len(name) > 255:
        raise AppError("markdown_name_too_long", "The name is too long", 400)
    return name


def _payload(file_asset: FileAsset, content: str, *, editable: bool = True) -> dict:
    from app.schemas.file_asset import FileAssetPublic

    return {"file": FileAssetPublic.model_validate(file_asset).model_dump(mode="json"), "content": content, "editable": editable}


def _decode(plain_bytes: bytes) -> tuple[str, bool]:
    """Text to show and whether it may be edited. Only UTF-8 round-trips safely: saving anything else
    (e.g. a GBK file from an old Windows editor) would replace the original with garbled text."""
    try:
        return plain_bytes.decode("utf-8-sig"), True
    except UnicodeDecodeError:
        pass
    try:
        return plain_bytes.decode("gb18030"), False
    except UnicodeDecodeError:
        return plain_bytes.decode("utf-8", "replace"), False


async def _markdown_file(db: AsyncSession, user: User, file_id: UUID) -> FileAsset:
    file_asset = await get_owned_file(db, user, file_id)
    if not is_markdown_file(file_asset):
        raise AppError("not_markdown", "Only .md files can be opened in the editor", 400)
    return file_asset


async def _refresh_search_text(db: AsyncSession, file_asset: FileAsset, content: str) -> None:
    """Keep keyword search in step with the saved text, reusing the file's latest extraction task."""
    task = await db.scalar(
        select(DocumentIntelligenceTask)
        .where(DocumentIntelligenceTask.file_id == file_asset.id)
        .order_by(DocumentIntelligenceTask.created_at.desc())
        .limit(1)
    )
    now = datetime.now(UTC)
    if task is None:
        task = DocumentIntelligenceTask(owner_id=file_asset.owner_id, file_id=file_asset.id, source_type="document", status="completed")
        db.add(task)
    task.status = "completed"
    task.raw_text = content
    task.error_message = None
    task.finished_at = now
    await db.flush()
    await db.execute(delete(DocumentTextChunk).where(DocumentTextChunk.file_id == file_asset.id))
    for index, text in enumerate(chunk_text(content) if content.strip() else []):
        db.add(DocumentTextChunk(owner_id=file_asset.owner_id, file_id=file_asset.id, task_id=task.id, chunk_index=index, page_number=None, text=text, created_at=now))


async def create_markdown(db: AsyncSession, user: User, *, name: str, content: str, folder_id: UUID | None) -> dict:
    require_pro(user)
    if folder_id is not None:
        folder = await db.scalar(select(Folder.id).where(Folder.id == folder_id, Folder.owner_id == user.id))
        if folder is None:
            raise AppError("folder_not_found", "Folder not found", 404)
    filename = _filename(name)
    file_asset = await create_encrypted_asset_from_bytes(
        db,
        owner=user,
        plain_bytes=_encode(content),
        original_filename=filename,
        mime_type=MARKDOWN_MIME,
        source=SOURCE,
        folder_id=folder_id,
        file_category="document",
    )
    await _refresh_search_text(db, file_asset, content)
    await write_audit_log(db, action="file.markdown_create", actor_user_id=user.id, target_type="file", target_id=str(file_asset.id), metadata_json={"filename": filename})
    await db.commit()
    await db.refresh(file_asset)
    return _payload(file_asset, content)


async def read_markdown(db: AsyncSession, user: User, file_id: UUID) -> dict:
    require_pro(user)
    file_asset = await _markdown_file(db, user, file_id)
    content, editable = _decode(decrypt_file_asset(file_asset))
    return _payload(file_asset, content, editable=editable)


async def save_markdown(db: AsyncSession, user: User, file_id: UUID, *, content: str, base_sha256: str | None) -> dict:
    require_pro(user)
    file_asset = await _markdown_file(db, user, file_id)
    if not _decode(decrypt_file_asset(file_asset))[1]:
        raise AppError("markdown_not_utf8", "This file is not UTF-8 text, so it can only be viewed online", 400)
    plain_bytes = _encode(content)
    new_hash = hashlib.sha256(plain_bytes).hexdigest()
    if new_hash == file_asset.sha256_hash:
        return _payload(file_asset, content)
    if base_sha256 is not None and base_sha256 != file_asset.sha256_hash:
        # Saved from another tab or device since this copy was opened: don't overwrite it silently.
        raise AppError("markdown_changed_elsewhere", "This document was changed somewhere else", 409)
    growth = len(plain_bytes) - file_asset.file_size
    if growth > 0:
        await ensure_storage_quota(db, user, growth)

    # Write the new ciphertext beside the old one; the old blob is only removed once the row points at the new one.
    file_key = generate_file_key()
    ciphertext, nonce, auth_tag = encrypt_bytes(plain_bytes, file_key)
    base_path = encrypted_file_path(user.id, file_asset.id)
    new_path = base_path.with_name(f"{file_asset.id}-{uuid4().hex[:12]}.bin")
    await save_encrypted_file(new_path, ciphertext)
    old_path = file_asset.encrypted_path
    try:
        file_asset.encrypted_path = str(new_path)
        file_asset.encrypted_file_key = wrap_file_key(file_key)
        file_asset.nonce = nonce
        file_asset.auth_tag = auth_tag
        file_asset.file_size = len(plain_bytes)
        file_asset.sha256_hash = new_hash
        file_asset.mime_type = MARKDOWN_MIME
        file_asset.updated_at = datetime.now(UTC)
        await _refresh_search_text(db, file_asset, content)
        await write_audit_log(db, action="file.markdown_save", actor_user_id=user.id, target_type="file", target_id=str(file_asset.id), metadata_json={"size": len(plain_bytes)})
        await db.commit()
    except Exception:
        await db.rollback()
        delete_physical_file(str(new_path))
        raise
    delete_physical_file(old_path)
    await db.refresh(file_asset)
    return _payload(file_asset, content)
