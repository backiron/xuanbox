"""Turn the text in a photo into a note: OCR in the worker, tidied by the local model for Pro users.

The note keeps the photo under the text so the reading can be checked against the original.
"""

from io import BytesIO
from uuid import UUID

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.note import Note
from app.models.user import User
from app.models.worker_task import WorkerTask
from app.services.note_ai_service import tidy_note_text
from app.services.note_service import MAX_BODY_CHARS, store_image
from app.services.ocr_service import extract_receipt_image_text
from app.services.photo_service import decrypt_photo_variant, get_owned_photo
from app.services.worker_service import enqueue_worker_task, mark_task_completed, mark_task_failed

PHOTO_NOTE_TASK_TYPE = "photo_to_note"
NO_TEXT = "no_text"


def _public(task: WorkerTask) -> dict:
    payload = task.payload_json or {}
    return {
        "id": str(task.id),
        "status": task.status,
        "note_id": payload.get("note_id"),
        "ai_assisted": bool(payload.get("ai_assisted")),
        "error": task.error_message,
    }


async def create_photo_note_task(db: AsyncSession, owner: User, photo_id: UUID) -> dict:
    photo = await get_owned_photo(db, owner, photo_id)
    existing = await db.scalar(
        select(WorkerTask)
        .where(
            WorkerTask.owner_id == owner.id,
            WorkerTask.task_type == PHOTO_NOTE_TASK_TYPE,
            WorkerTask.target_id == photo.id,
            WorkerTask.status.in_(("pending", "processing")),
        )
        .limit(1)
    )
    if existing:
        return _public(existing)
    task = await enqueue_worker_task(
        db,
        task_type=PHOTO_NOTE_TASK_TYPE,
        owner_id=owner.id,
        target_type="photo",
        target_id=photo.id,
        payload_json={"photo_id": str(photo.id)},
    )
    await db.commit()
    await db.refresh(task)
    return _public(task)


async def get_photo_note_task(db: AsyncSession, owner: User, task_id: UUID) -> dict:
    task = await db.get(WorkerTask, task_id)
    if task is None or task.owner_id != owner.id or task.task_type != PHOTO_NOTE_TASK_TYPE:
        raise AppError("photo_note_task_not_found", "Task not found", 404)
    return _public(task)


def _read_text(image_bytes: bytes) -> str:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            return extract_receipt_image_text(image).strip()
    except UnidentifiedImageError as exc:
        raise ValueError(f"Image OCR failed: {exc}") from exc


async def process_photo_note_task(db: AsyncSession, task: WorkerTask) -> None:
    try:
        owner = await db.get(User, task.owner_id)
        if owner is None:
            raise AppError("photo_not_found", "Photo not found", 404)
        photo_id = UUID((task.payload_json or {}).get("photo_id"))
        _, original = await decrypt_photo_variant(db, owner, photo_id, "original")
        raw_text = _read_text(original)
        if not raw_text:
            await mark_task_failed(db, task, NO_TEXT)
            return
        tidied = await tidy_note_text(raw_text) if owner.plan == "pro" else None
        title, text = tidied or ("", raw_text)
        _, preview = await decrypt_photo_variant(db, owner, photo_id, "preview")
        # A failure past this point must not leave an empty note behind.
        async with db.begin_nested():
            note = Note(owner_id=owner.id, body="")
            db.add(note)
            await db.flush()
            image = await store_image(db, owner, note, preview)
            marker = f"[[img:{image.id}]]"
            text = text[: MAX_BODY_CHARS - len(title) - len(marker) - 4]
            note.body = f"{title}\n{text}\n\n{marker}" if title else f"{text}\n\n{marker}"
        task.payload_json = {**(task.payload_json or {}), "note_id": str(note.id), "ai_assisted": tidied is not None}
        await mark_task_completed(db, task)
    except Exception as exc:
        await mark_task_failed(db, task, str(exc))
