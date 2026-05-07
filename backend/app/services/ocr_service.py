import re
from io import BytesIO
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image, UnidentifiedImageError
import pytesseract

from app.core.errors import AppError
from app.models.file_asset import FileAsset
from app.models.ocr_task import OcrTask
from app.models.receipt import Receipt
from app.models.user import User
from app.models.worker_task import WorkerTask
from app.schemas.ocr import OcrConfirmRequest
from app.services.file_service import decrypt_file_asset
from app.services.worker_service import enqueue_worker_task, mark_task_completed, mark_task_failed

OCR_TASK_TYPE = "receipt_ocr"
OCR_STATUSES = {"pending", "processing", "completed", "failed", "confirmed"}


async def get_owned_receipt(db: AsyncSession, owner: User, receipt_id: UUID) -> Receipt:
    receipt = await db.scalar(select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == owner.id))
    if receipt is None:
        raise AppError("receipt_not_found", "Receipt not found", 404)
    return receipt


async def create_receipt_ocr_task(db: AsyncSession, owner: User, receipt_id: UUID) -> OcrTask:
    receipt = await get_owned_receipt(db, owner, receipt_id)
    existing = await db.scalar(
        select(OcrTask)
        .where(OcrTask.receipt_id == receipt.id, OcrTask.status.in_(("pending", "processing")))
        .order_by(OcrTask.created_at.desc())
        .limit(1)
    )
    if existing:
        return existing
    task = OcrTask(
        owner_id=owner.id,
        file_id=receipt.file_id,
        receipt_id=receipt.id,
        status="pending",
        created_at=datetime.now(UTC),
    )
    receipt.ocr_status = "pending"
    db.add(task)
    await db.flush()
    await enqueue_worker_task(
        db,
        task_type=OCR_TASK_TYPE,
        owner_id=owner.id,
        target_type="ocr_task",
        target_id=task.id,
        payload_json={"ocr_task_id": str(task.id)},
    )
    await db.commit()
    await db.refresh(task)
    return task


async def list_receipt_ocr_tasks(db: AsyncSession, owner: User, receipt_id: UUID) -> list[OcrTask]:
    await get_owned_receipt(db, owner, receipt_id)
    result = await db.scalars(
        select(OcrTask)
        .where(OcrTask.owner_id == owner.id, OcrTask.receipt_id == receipt_id)
        .order_by(OcrTask.created_at.desc())
    )
    return list(result)


async def get_owned_ocr_task(db: AsyncSession, owner: User, receipt_id: UUID, task_id: UUID) -> OcrTask:
    task = await db.scalar(
        select(OcrTask).where(OcrTask.id == task_id, OcrTask.owner_id == owner.id, OcrTask.receipt_id == receipt_id)
    )
    if task is None:
        raise AppError("ocr_task_not_found", "OCR task not found", 404)
    return task


async def retry_ocr_task(db: AsyncSession, owner: User, receipt_id: UUID, task_id: UUID) -> OcrTask:
    task = await get_owned_ocr_task(db, owner, receipt_id, task_id)
    if task.status != "failed":
        raise AppError("ocr_retry_not_allowed", "Only failed OCR tasks can be retried", 400)
    task.status = "pending"
    task.error_message = None
    task.finished_at = None
    receipt = await get_owned_receipt(db, owner, receipt_id)
    receipt.ocr_status = "pending"
    await enqueue_worker_task(
        db,
        task_type=OCR_TASK_TYPE,
        owner_id=owner.id,
        target_type="ocr_task",
        target_id=task.id,
        payload_json={"ocr_task_id": str(task.id)},
    )
    await db.commit()
    await db.refresh(task)
    return task


async def confirm_ocr_task(db: AsyncSession, owner: User, receipt_id: UUID, task_id: UUID, payload: OcrConfirmRequest) -> OcrTask:
    task = await get_owned_ocr_task(db, owner, receipt_id, task_id)
    if task.status not in {"completed", "confirmed"}:
        raise AppError("ocr_not_ready", "OCR task is not ready to confirm", 400)
    receipt = await get_owned_receipt(db, owner, receipt_id)
    parsed = task.parsed_json or {}
    receipt.merchant = payload.merchant if "merchant" in payload.model_fields_set else parsed.get("merchant") or receipt.merchant
    receipt.category = payload.category if "category" in payload.model_fields_set else parsed.get("category") or receipt.category
    receipt.amount = payload.amount if "amount" in payload.model_fields_set else _decimal_or_none(parsed.get("amount")) or receipt.amount
    receipt.currency = payload.currency if "currency" in payload.model_fields_set else parsed.get("currency") or receipt.currency
    receipt.purchase_date = payload.purchase_date if "purchase_date" in payload.model_fields_set else _date_or_none(parsed.get("purchase_date")) or receipt.purchase_date
    receipt.warranty_until = payload.warranty_until if "warranty_until" in payload.model_fields_set else receipt.warranty_until
    receipt.notes = payload.notes if "notes" in payload.model_fields_set else receipt.notes
    receipt.ocr_status = "confirmed"
    task.status = "confirmed"
    task.confirmed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(task)
    return task


def extract_text_from_bytes(file_asset: FileAsset, plain_bytes: bytes) -> str:
    mime_type = file_asset.mime_type or ""
    if mime_type.startswith("text/") or file_asset.file_ext in {"txt", "csv", "md"}:
        return plain_bytes.decode("utf-8", "ignore").strip()
    if mime_type.startswith("image/") or file_asset.file_ext in {"jpg", "jpeg", "png", "webp", "tif", "tiff", "bmp"}:
        try:
            with Image.open(BytesIO(plain_bytes)) as image:
                image = image.convert("L")
                return pytesseract.image_to_string(image, lang="eng+chi_sim").strip()
        except (UnidentifiedImageError, pytesseract.TesseractError) as exc:
            raise ValueError(f"Image OCR failed: {exc}") from exc
    if file_asset.file_ext == "pdf" or mime_type == "application/pdf":
        decoded = plain_bytes.decode("latin-1", "ignore")
        tokens = re.findall(r"[A-Za-z0-9$.,:/\\-]{3,}", decoded)
        return " ".join(tokens[:400]).strip()
    raise ValueError("OCR engine is not configured for this file type yet")


def parse_receipt_text(raw_text: str) -> dict:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    merchant = lines[0][:160] if lines else None
    amount_match = re.search(r"(?:total|amount|paid)?\s*([$€£]|USD|CAD|CNY|RMB)?\s*(\d+[.,]\d{2})", raw_text, re.IGNORECASE)
    date_match = re.search(r"(20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]20\d{2})", raw_text)
    currency = "USD"
    amount = None
    if amount_match:
        marker = amount_match.group(1)
        amount = amount_match.group(2).replace(",", ".")
        if marker in {"CAD", "CNY", "RMB", "USD"}:
            currency = "CNY" if marker == "RMB" else marker
        elif marker == "€":
            currency = "EUR"
        elif marker == "£":
            currency = "GBP"
    return {
        "merchant": merchant,
        "amount": amount,
        "currency": currency,
        "purchase_date": _normalize_date(date_match.group(1)) if date_match else None,
        "raw_text_preview": raw_text[:500],
    }


async def process_receipt_ocr_task(db: AsyncSession, task: WorkerTask) -> None:
    ocr_task_id = UUID((task.payload_json or {}).get("ocr_task_id"))
    ocr_task = await db.get(OcrTask, ocr_task_id)
    if ocr_task is None:
        raise AppError("ocr_task_not_found", "OCR task not found", 404)
    receipt = await db.get(Receipt, ocr_task.receipt_id)
    file_asset = await db.get(FileAsset, ocr_task.file_id)
    if receipt is None or file_asset is None or file_asset.is_deleted:
        raise AppError("ocr_target_not_found", "OCR target no longer exists", 404)
    try:
        ocr_task.status = "processing"
        receipt.ocr_status = "processing"
        plain_bytes = decrypt_file_asset(file_asset)
        raw_text = extract_text_from_bytes(file_asset, plain_bytes)
        if not raw_text:
            raise ValueError("No readable text found")
        ocr_task.raw_text = raw_text
        ocr_task.parsed_json = parse_receipt_text(raw_text)
        ocr_task.status = "completed"
        ocr_task.finished_at = datetime.now(UTC)
        ocr_task.error_message = None
        receipt.ocr_status = "completed"
        await mark_task_completed(db, task)
    except Exception as exc:
        message = str(exc)
        ocr_task.status = "failed"
        ocr_task.error_message = message
        ocr_task.finished_at = datetime.now(UTC)
        receipt.ocr_status = "failed"
        await mark_task_failed(db, task, message)


def _normalize_date(value: str) -> str | None:
    normalized = value.replace("/", "-")
    parts = normalized.split("-")
    if len(parts[0]) == 4:
        year, month, day = parts
    else:
        month, day, year = parts
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except ValueError:
        return None


def _decimal_or_none(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value))


def _date_or_none(value: object) -> date | None:
    if not value:
        return None
    return date.fromisoformat(str(value))
