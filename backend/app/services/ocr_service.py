import re
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from uuid import UUID

import pytesseract
from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.file_asset import FileAsset
from app.models.ocr_task import OcrTask
from app.models.receipt import Receipt
from app.models.user import User
from app.models.worker_task import WorkerTask
from app.schemas.ocr import OcrConfirmRequest
from app.services.file_service import decrypt_file_asset
from app.services.receipt_ai_service import enhance_receipt_parse
from app.services.worker_service import enqueue_worker_task, mark_task_completed, mark_task_failed

OCR_TASK_TYPE = "receipt_ocr"
OCR_STATUSES = {"pending", "processing", "completed", "failed", "confirmed"}
_rapid_ocr_engine = None


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
    if task.status in {"pending", "processing"}:
        raise AppError("ocr_retry_not_allowed", "OCR task is already queued or running", 400)
    task.status = "pending"
    task.raw_text = None
    task.parsed_json = None
    task.error_message = None
    task.finished_at = None
    task.confirmed_at = None
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


async def confirm_ocr_task(
    db: AsyncSession,
    owner: User,
    receipt_id: UUID,
    task_id: UUID,
    payload: OcrConfirmRequest,
) -> OcrTask:
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
    receipt.warranty_until = payload.warranty_until if "warranty_until" in payload.model_fields_set else _date_or_none(parsed.get("warranty_until")) or receipt.warranty_until
    receipt.notes = payload.notes if "notes" in payload.model_fields_set else parsed.get("notes") or receipt.notes
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
                return extract_receipt_image_text(image)
        except (UnidentifiedImageError, pytesseract.TesseractError) as exc:
            raise ValueError(f"Image OCR failed: {exc}") from exc
    if file_asset.file_ext == "pdf" or mime_type == "application/pdf":
        decoded = plain_bytes.decode("latin-1", "ignore")
        tokens = re.findall(r"[A-Za-z0-9$.,:/\\-]{3,}", decoded)
        return " ".join(tokens[:600]).strip()
    raise ValueError("OCR engine is not configured for this file type yet")


def extract_receipt_image_text(image: Image.Image) -> str:
    base = ImageOps.exif_transpose(image).convert("RGB")
    crop = _crop_bright_receipt_region(base)
    rapid_texts = [
        _extract_with_rapidocr(crop),
        _extract_with_rapidocr(_center_crop(base, 0.72, 0.98)),
        _extract_with_rapidocr(_center_crop(base, 0.56, 0.98)),
        _extract_with_rapidocr(base),
    ]
    rapid_text = max(rapid_texts, key=_ocr_text_score, default="").strip()
    if _ocr_text_score(rapid_text) >= 8:
        return rapid_text
    candidates = [
        _prepare_ocr_image(crop, threshold=False),
        _prepare_ocr_image(crop, threshold=True),
        _prepare_ocr_image(base, threshold=False),
    ]
    results: list[str] = []
    for candidate in candidates:
        for psm in (6, 4, 11):
            text = pytesseract.image_to_string(
                candidate,
                lang="eng+chi_sim",
                config=f"--oem 3 --psm {psm}",
            ).strip()
            if text:
                results.append(text)
    if not results:
        return ""
    return max(results, key=_ocr_text_score).strip()


def extract_document_image_text_candidates(image: Image.Image) -> list[tuple[str, str]]:
    base = ImageOps.exif_transpose(image).convert("RGB")
    width, height = base.size
    crop = _crop_bright_receipt_region(base)
    lower = base.crop((0, int(height * 0.28), width, height))
    lower_deep = base.crop((0, int(height * 0.36), width, height))
    candidates: list[tuple[str, str]] = [
        ("overall-rapid", _extract_with_rapidocr(base)),
        ("cropped-rapid", _extract_with_rapidocr(crop)),
    ]
    for label, candidate in (
        ("overall", base),
        ("cropped", crop),
        ("handwriting-area", lower),
        ("lower-handwriting-area", lower_deep),
    ):
        prepared = _prepare_ocr_image(candidate, threshold=False)
        for image_label, image_candidate in ((label, candidate), (f"{label}-enhanced", prepared)):
            for psm in (4, 6, 11, 12):
                try:
                    text = pytesseract.image_to_string(
                        image_candidate,
                        lang="eng+chi_sim",
                        config=f"--oem 3 --psm {psm}",
                    ).strip()
                except pytesseract.TesseractError:
                    text = ""
                if text:
                    candidates.append((f"{image_label}-psm{psm}", text))
    unique: dict[str, str] = {}
    for label, text in candidates:
        normalized = _clean_ocr_candidate(text)
        if normalized and normalized not in unique.values():
            unique[label] = normalized
    return sorted(unique.items(), key=lambda item: _document_ocr_quality_score(item[1]), reverse=True)[:4]


def extract_document_image_text(image: Image.Image) -> str:
    candidates = extract_document_image_text_candidates(image)
    return candidates[0][1] if candidates else ""


def _center_crop(image: Image.Image, width_ratio: float, height_ratio: float) -> Image.Image:
    width, height = image.size
    crop_width = int(width * width_ratio)
    crop_height = int(height * height_ratio)
    left = max(0, (width - crop_width) // 2)
    top = max(0, (height - crop_height) // 2)
    return image.crop((left, top, min(width, left + crop_width), min(height, top + crop_height)))


def _extract_with_rapidocr(image: Image.Image) -> str:
    global _rapid_ocr_engine
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception:
        return ""
    if _rapid_ocr_engine is None:
        _rapid_ocr_engine = RapidOCR()
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    try:
        result, _ = _rapid_ocr_engine(image_bytes.getvalue())
    except Exception:
        return ""
    if not result:
        return ""
    rows = []
    for item in result:
        if len(item) < 2 or not isinstance(item[1], str):
            continue
        box = item[0]
        text = item[1].strip()
        if not text:
            continue
        try:
            y_pos = min(point[1] for point in box)
            x_pos = min(point[0] for point in box)
        except Exception:
            y_pos = 0
            x_pos = 0
        rows.append((y_pos, x_pos, text))
    rows.sort(key=lambda row: (row[0], row[1]))
    return "\n".join(row[2] for row in rows)


def _crop_bright_receipt_region(image: Image.Image) -> Image.Image:
    grayscale = image.convert("L")
    mask = grayscale.point(lambda pixel: 255 if pixel > 135 else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return image
    left, top, right, bottom = bbox
    width, height = image.size
    crop_width = right - left
    crop_height = bottom - top
    if crop_width < width * 0.18 or crop_height < height * 0.25:
        return image
    pad_x = max(12, int(crop_width * 0.04))
    pad_y = max(12, int(crop_height * 0.04))
    return image.crop(
        (
            max(0, left - pad_x),
            max(0, top - pad_y),
            min(width, right + pad_x),
            min(height, bottom + pad_y),
        )
    )


def _prepare_ocr_image(image: Image.Image, *, threshold: bool) -> Image.Image:
    grayscale = ImageOps.grayscale(image)
    grayscale = ImageOps.autocontrast(grayscale, cutoff=1)
    target_width = 1800
    if grayscale.width < target_width:
        scale = target_width / grayscale.width
        grayscale = grayscale.resize((target_width, int(grayscale.height * scale)), Image.Resampling.LANCZOS)
    grayscale = grayscale.filter(ImageFilter.SHARPEN)
    if threshold:
        grayscale = grayscale.point(lambda pixel: 255 if pixel > 172 else 0)
    return grayscale


def _clean_ocr_candidate(text: str) -> str:
    lines = []
    for line in text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if not clean:
            continue
        if len(clean) <= 2 and not re.search(r"[A-Za-z0-9\u4e00-\u9fff]", clean):
            continue
        lines.append(clean)
    return "\n".join(lines).strip()


def _document_ocr_quality_score(text: str) -> int:
    if not text:
        return 0
    alnum = len(re.findall(r"[A-Za-z0-9\u4e00-\u9fff]", text))
    noise = len(re.findall(r"[^\w\s\u4e00-\u9fff.,:/()\\-+#>]", text))
    line_count = len([line for line in text.splitlines() if line.strip()])
    score = alnum + min(line_count, 24) * 4
    score += 12 * len(re.findall(r"\b(day|drops?|water|compress|minute|min|complete|systane|drink|breaks?)\b", text, re.IGNORECASE))
    score -= noise * 3
    score -= max(0, len(text) - 2400) // 8
    return score


def _ocr_text_score(text: str) -> int:
    lower = text.lower()
    score = len(re.findall(r"[A-Za-z0-9\u4e00-\u9fff]{2,}", text))
    score += 8 * len(re.findall(r"\d+[.,]\d{2}", text))
    score += 12 * sum(1 for word in ("total", "subtotal", "tax", "visa", "amount", "receipt") if word in lower)
    return score


def parse_receipt_text(raw_text: str) -> dict:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    amount, currency = _guess_amount_and_currency(raw_text)
    return {
        "merchant": _guess_merchant(lines),
        "amount": amount,
        "currency": currency,
        "purchase_date": _guess_purchase_date(raw_text),
        "category": _guess_category(raw_text),
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
        parsed = parse_receipt_text(raw_text)
        owner = await db.get(User, ocr_task.owner_id)
        ai_fields = await enhance_receipt_parse(raw_text, parsed) if owner and owner.plan == "pro" else {}
        ocr_task.raw_text = raw_text
        ocr_task.parsed_json = _merge_ai_fields(parsed, ai_fields)
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


def _guess_merchant(lines: list[str]) -> str | None:
    skip_patterns = (
        "invoice",
        "receipt",
        "transaction",
        "tel",
        "phone",
        "gst",
        "hst",
        "pst",
        "tax",
        "address",
        "www.",
        "http",
    )
    for line in lines[:10]:
        compact = re.sub(r"\s+", " ", line).strip(" -*#")
        if len(compact) < 2 or re.search(r"\d{5,}", compact):
            continue
        lower = compact.lower()
        if any(pattern in lower for pattern in skip_patterns):
            continue
        return compact[:160]
    return lines[0][:160] if lines else None


def _guess_amount_and_currency(raw_text: str) -> tuple[str | None, str]:
    currency = "USD"
    upper = raw_text.upper()
    if "CAD" in upper or "CANADA" in upper or "GST" in upper or "HST" in upper:
        currency = "CAD"
    if "CNY" in upper or "RMB" in upper:
        currency = "CNY"
    if "EUR" in upper:
        currency = "EUR"
    if "GBP" in upper:
        currency = "GBP"

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if re.fullmatch(r"(?i)(total|grand\s*total|amount\s*paid|balance|due)", line):
            for next_line in lines[index + 1 : index + 4]:
                match = re.search(r"(?P<marker>USD|CAD|CNY|RMB|\$)?\s*(?P<amount>\d{1,5}[,.]\d{2})", next_line, re.IGNORECASE)
                if match:
                    marker = match.group("marker")
                    if marker in {"CAD", "CNY", "RMB", "USD"}:
                        currency = "CNY" if marker == "RMB" else marker
                    return match.group("amount").replace(",", "."), currency

    amount_pattern = re.compile(
        r"(?P<label>total|amount\s*paid|balance|grand\s*total|payment|paid|due)?"
        r"[^\dA-Z]{0,12}(?P<marker>USD|CAD|CNY|RMB|\$)?\s*(?P<amount>\d{1,5}[,.]\d{2})",
        re.IGNORECASE,
    )
    candidates: list[tuple[int, str, str | None]] = []
    for match in amount_pattern.finditer(raw_text):
        value = match.group("amount").replace(",", ".")
        label = (match.group("label") or "").lower()
        marker = match.group("marker")
        score = 1
        if label:
            score += 10
        context = raw_text[max(0, match.start() - 24) : match.end() + 24].lower()
        if "subtotal" in context or "tax" in context or "suggested" in context:
            score -= 3
        candidates.append((score, value, marker))
    if not candidates:
        return None, currency
    candidates.sort(key=lambda item: (item[0], Decimal(item[1])), reverse=True)
    marker = candidates[0][2]
    if marker in {"CAD", "CNY", "RMB", "USD"}:
        currency = "CNY" if marker == "RMB" else marker
    return candidates[0][1], currency


def _guess_purchase_date(raw_text: str) -> str | None:
    patterns = (
        r"20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}",
        r"\d{1,2}[-/.]\d{1,2}[-/.]20\d{2}",
        r"\d{1,2}[-/.]\d{1,2}[-/.]\d{2}",
    )
    for pattern in patterns:
        match = re.search(pattern, raw_text)
        if not match:
            continue
        value = match.group(0).replace(".", "-").replace("/", "-")
        parts = value.split("-")
        if len(parts[-1]) == 2:
            parts[-1] = f"20{parts[-1]}"
            value = "-".join(parts)
        normalized = _normalize_date(value)
        if normalized:
            return normalized
    return None


def _guess_category(raw_text: str) -> str | None:
    lower = raw_text.lower()
    categories = (
        ("restaurant", ("restaurant", "cafe", "coffee", "mcdonald", "tim hortons", "starbucks")),
        ("restaurant", ("ramen", "curry", "salad", "crab", "food", "dining")),
        ("fuel", ("gas", "fuel", "esso", "petro", "chevron", "mobil")),
        ("groceries", ("grocery", "superstore", "walmart", "costco", "sobeys", "save-on-foods")),
        ("pharmacy", ("pharmacy", "drug", "shoppers", "rexall")),
        ("electronics", ("electronics", "best buy", "memory express", "apple")),
        ("office", ("office", "staples", "stationery")),
    )
    for category, keywords in categories:
        if any(keyword in lower for keyword in keywords):
            return category
    return None


def _merge_ai_fields(parsed: dict, ai_fields: dict) -> dict:
    if not ai_fields:
        return parsed
    allowed_fields = {"merchant", "category", "amount", "currency", "purchase_date", "warranty_until", "notes", "items_summary"}
    merged = dict(parsed)
    for field in allowed_fields:
        value = ai_fields.get(field)
        if value not in (None, ""):
            merged[field] = str(value)[:1000] if field in {"notes", "items_summary"} else value
    merged["ai_assisted"] = True
    return merged


def _normalize_date(value: str) -> str | None:
    normalized = value.replace("/", "-").replace(".", "-")
    parts = normalized.split("-")
    if len(parts) != 3:
        return None
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
