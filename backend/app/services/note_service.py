"""Quick notes: plain text with images on their own lines.

The body is plain text; an image sits on a line of its own as ``[[img:<image id>]]``. Images are encrypted
like library files and stored under ``encrypted_files/`` so they are part of every backup.
"""

import re
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import UploadFile
from PIL import Image, ImageOps
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.models.note import Note, NoteImage
from app.models.user import User
from app.services.encryption_service import decrypt_bytes, encrypt_bytes, generate_file_key, unwrap_file_key, wrap_file_key
from app.services.storage_service import delete_physical_file, read_encrypted_file, save_encrypted_file
from app.services.upload_limits import MAX_IMAGE_UPLOAD_BYTES, read_upload_bytes

IMAGE_LINE = re.compile(r"^\[\[img:([0-9a-fA-F-]{36})\]\]$", re.MULTILINE)
MAX_BODY_CHARS = 200_000
MAX_IMAGES_PER_NOTE = 60
# Large phone photos are scaled down; a note is for reading, not for keeping originals.
MAX_IMAGE_SIDE = 2560
KEEP_AS_IS = {"JPEG": "image/jpeg", "PNG": "image/png", "GIF": "image/gif", "WEBP": "image/webp"}
# An image uploaded but not (yet) placed in the body is kept this long, so a save in flight cannot lose it.
UNPLACED_GRACE = timedelta(minutes=10)


def image_ids_in(body: str) -> set[UUID]:
    ids = set()
    for match in IMAGE_LINE.finditer(body):
        try:
            ids.add(UUID(match.group(1)))
        except ValueError:
            continue
    return ids


def plain_text(body: str) -> str:
    return IMAGE_LINE.sub("", body).strip()


def _summary(note: Note, image_ids: list[UUID]) -> dict[str, Any]:
    lines = [line.strip() for line in plain_text(note.body).splitlines() if line.strip()]
    return {
        "id": str(note.id),
        "title": lines[0][:120] if lines else "",
        "snippet": " ".join(lines[1:])[:240],
        "pinned": note.pinned,
        "image_count": len(image_ids),
        "cover_image_id": str(image_ids[0]) if image_ids else None,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
    }


def _detail(note: Note) -> dict[str, Any]:
    return {
        "id": str(note.id),
        "body": note.body,
        "pinned": note.pinned,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
    }


async def _get_note(db: AsyncSession, user: User, note_id: UUID) -> Note:
    note = await db.get(Note, note_id)
    if note is None or note.owner_id != user.id:
        raise AppError("note_not_found", "Note not found", 404)
    return note


async def list_notes(db: AsyncSession, user: User, query: str | None = None) -> list[dict[str, Any]]:
    statement = select(Note).where(Note.owner_id == user.id)
    words = (query or "").split()
    for word in words[:8]:
        escaped = word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(Note.body.ilike(f"%{escaped}%", escape="\\"))
    notes = list(await db.scalars(statement.order_by(Note.pinned.desc(), Note.updated_at.desc()).limit(500)))
    return [_summary(note, _ordered_image_ids(note.body)) for note in notes]


def _ordered_image_ids(body: str) -> list[UUID]:
    seen: list[UUID] = []
    for match in IMAGE_LINE.finditer(body):
        try:
            image_id = UUID(match.group(1))
        except ValueError:
            continue
        if image_id not in seen:
            seen.append(image_id)
    return seen


async def create_note(db: AsyncSession, user: User, body: str = "") -> dict[str, Any]:
    _check_body(body)
    if image_ids_in(body):
        raise AppError("note_image_not_found", "Add images after the note is created", 400)
    note = Note(owner_id=user.id, body=body)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return _detail(note)


async def get_note(db: AsyncSession, user: User, note_id: UUID) -> dict[str, Any]:
    return _detail(await _get_note(db, user, note_id))


def _check_body(body: str) -> None:
    if len(body) > MAX_BODY_CHARS:
        raise AppError("note_too_long", f"A note can hold up to {MAX_BODY_CHARS} characters", 413)


async def update_note(
    db: AsyncSession,
    user: User,
    note_id: UUID,
    *,
    body: str | None = None,
    pinned: bool | None = None,
    base_updated_at: datetime | None = None,
) -> dict[str, Any]:
    note = await _get_note(db, user, note_id)
    if body is not None and body != note.body:
        if base_updated_at is not None and note.updated_at > base_updated_at + timedelta(milliseconds=1):
            # Edited on another device since this copy was opened: don't overwrite it silently.
            raise AppError("note_changed_elsewhere", "This note was changed on another device", 409)
        _check_body(body)
        referenced = image_ids_in(body)
        if referenced:
            owned = set(await db.scalars(select(NoteImage.id).where(NoteImage.note_id == note.id, NoteImage.id.in_(referenced))))
            if referenced - owned:
                raise AppError("note_image_not_found", "An image in this note no longer exists", 400)
        note.body = body
        await _drop_unplaced_images(db, note, referenced)
    if pinned is not None:
        note.pinned = pinned
    await db.commit()
    await db.refresh(note)
    return _detail(note)


async def _drop_unplaced_images(db: AsyncSession, note: Note, placed: set[UUID]) -> None:
    cutoff = datetime.now(UTC) - UNPLACED_GRACE
    statement = select(NoteImage).where(NoteImage.note_id == note.id, NoteImage.created_at < cutoff)
    if placed:
        statement = statement.where(NoteImage.id.not_in(placed))
    for image in await db.scalars(statement):
        delete_physical_file(image.encrypted_path)
        await db.delete(image)


async def delete_note(db: AsyncSession, user: User, note_id: UUID) -> None:
    note = await _get_note(db, user, note_id)
    paths = list(await db.scalars(select(NoteImage.encrypted_path).where(NoteImage.note_id == note.id)))
    await db.delete(note)
    await db.commit()
    for path in paths:
        delete_physical_file(path)


def _prepare_image(raw: bytes) -> tuple[bytes, str, int, int]:
    try:
        image = Image.open(BytesIO(raw))
        image_format = image.format
        width, height = image.size
    except Exception as exc:
        raise AppError("note_image_unsupported", "This file is not an image the browser can show", 415) from exc
    if image_format in KEEP_AS_IS and max(width, height) <= MAX_IMAGE_SIDE:
        return raw, KEEP_AS_IS[image_format], width, height
    try:
        image = ImageOps.exif_transpose(image)
        image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        buffer = BytesIO()
        if image.mode in ("RGBA", "LA", "P") and image_format == "PNG":
            image.save(buffer, format="PNG", optimize=True)
            mime = "image/png"
        else:
            image.convert("RGB").save(buffer, format="JPEG", quality=85, optimize=True)
            mime = "image/jpeg"
    except Exception as exc:
        raise AppError("note_image_unsupported", "This file is not an image the browser can show", 415) from exc
    return buffer.getvalue(), mime, image.size[0], image.size[1]


async def add_image(db: AsyncSession, user: User, note_id: UUID, upload: UploadFile) -> dict[str, Any]:
    note = await _get_note(db, user, note_id)
    count = await db.scalar(select(func.count()).select_from(NoteImage).where(NoteImage.note_id == note.id))
    if (count or 0) >= MAX_IMAGES_PER_NOTE:
        raise AppError("note_image_limit", f"A note can hold up to {MAX_IMAGES_PER_NOTE} images", 413)
    raw = await read_upload_bytes(upload, max_bytes=MAX_IMAGE_UPLOAD_BYTES)
    image = await store_image(db, user, note, raw)
    await db.commit()
    return {"id": str(image.id), "width": image.width, "height": image.height, "marker": f"[[img:{image.id}]]"}


async def store_image(db: AsyncSession, user: User, note: Note, raw: bytes) -> NoteImage:
    """Encrypt and save one image for ``note``; the caller commits and places its marker in the body."""
    content, mime, width, height = _prepare_image(raw)
    image_id = uuid4()
    key = generate_file_key()
    ciphertext, nonce, auth_tag = encrypt_bytes(content, key)
    path = Path(settings.STORAGE_ROOT) / "encrypted_files" / str(user.id) / "notes" / str(note.id) / f"{image_id}.bin"
    await save_encrypted_file(path, ciphertext)
    image = NoteImage(
        id=image_id,
        note_id=note.id,
        owner_id=user.id,
        mime_type=mime,
        file_size=len(content),
        width=width,
        height=height,
        encrypted_path=str(path),
        encrypted_file_key=wrap_file_key(key),
        nonce=nonce,
        auth_tag=auth_tag,
    )
    db.add(image)
    await db.flush()
    return image


async def read_image(db: AsyncSession, user: User, note_id: UUID, image_id: UUID) -> tuple[bytes, str]:
    image = await db.get(NoteImage, image_id)
    if image is None or image.note_id != note_id or image.owner_id != user.id:
        raise AppError("note_image_not_found", "Image not found", 404)
    content = decrypt_bytes(read_encrypted_file(image.encrypted_path), unwrap_file_key(image.encrypted_file_key), image.nonce, image.auth_tag)
    return content, image.mime_type
