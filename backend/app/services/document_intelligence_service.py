import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.document_intelligence import DocumentFieldValue, DocumentIntelligenceTask, DocumentProfile, DocumentTextChunk
from app.models.file_asset import FileAsset
from app.models.user import User
from app.models.worker_task import WorkerTask
from app.schemas.document_intelligence import DocumentProfileUpdateRequest
from app.services.document_ai_service import enhance_document_parse
from app.services.file_service import decrypt_file_asset, get_owned_file
from app.services.ocr_service import extract_receipt_image_text, extract_text_from_bytes
from app.services.worker_service import enqueue_worker_task, mark_task_completed, mark_task_failed

DOCUMENT_EXTRACT_TASK_TYPE = "document_extract_text"
SUPPORTED_EXTENSIONS = {"txt", "md", "csv", "pdf"}
SUPPORTED_CATEGORIES = {"document", "photo", "receipt", "other"}


def is_supported_file(file_asset: FileAsset) -> bool:
    mime_type = file_asset.mime_type or ""
    if file_asset.source in {"system_import", "avatar"}:
        return False
    if mime_type.startswith("image/"):
        return False
    if mime_type.startswith("text/"):
        return True
    return (file_asset.file_ext or "").lower() in SUPPORTED_EXTENSIONS and file_asset.file_category in SUPPORTED_CATEGORIES


async def enqueue_document_intelligence_task(
    db: AsyncSession,
    *,
    owner: User,
    file_asset: FileAsset,
    source_type: str = "file",
) -> DocumentIntelligenceTask | None:
    if not is_supported_file(file_asset):
        return None
    existing = await db.scalar(
        select(DocumentIntelligenceTask)
        .where(
            DocumentIntelligenceTask.owner_id == owner.id,
            DocumentIntelligenceTask.file_id == file_asset.id,
            DocumentIntelligenceTask.status.in_(("pending", "processing", "completed", "confirmed")),
        )
        .order_by(DocumentIntelligenceTask.created_at.desc())
        .limit(1)
    )
    if existing:
        return existing
    task = DocumentIntelligenceTask(
        owner_id=owner.id,
        file_id=file_asset.id,
        source_type=source_type,
        status="pending",
    )
    db.add(task)
    await db.flush()
    await enqueue_worker_task(
        db,
        task_type=DOCUMENT_EXTRACT_TASK_TYPE,
        owner_id=owner.id,
        target_type="document_intelligence_task",
        target_id=task.id,
        payload_json={"document_intelligence_task_id": str(task.id)},
    )
    return task


async def get_file_intelligence(
    db: AsyncSession,
    owner: User,
    file_id: UUID,
) -> tuple[list[DocumentIntelligenceTask], DocumentProfile | None, list[DocumentFieldValue], list[DocumentTextChunk]]:
    await get_owned_file(db, owner, file_id)
    tasks = list(
        await db.scalars(
            select(DocumentIntelligenceTask)
            .where(DocumentIntelligenceTask.owner_id == owner.id, DocumentIntelligenceTask.file_id == file_id)
            .order_by(DocumentIntelligenceTask.created_at.desc())
        )
    )
    profile = await db.scalar(select(DocumentProfile).where(DocumentProfile.owner_id == owner.id, DocumentProfile.file_id == file_id))
    fields = []
    if profile:
        fields = list(
            await db.scalars(
                select(DocumentFieldValue)
                .where(DocumentFieldValue.owner_id == owner.id, DocumentFieldValue.profile_id == profile.id)
                .order_by(DocumentFieldValue.field_key.asc())
            )
        )
    chunks = list(
        await db.scalars(
            select(DocumentTextChunk)
            .where(DocumentTextChunk.owner_id == owner.id, DocumentTextChunk.file_id == file_id)
            .order_by(DocumentTextChunk.chunk_index.asc())
            .limit(20)
        )
    )
    return tasks, profile, fields, chunks


async def update_file_intelligence_profile(
    db: AsyncSession,
    owner: User,
    file_id: UUID,
    payload: DocumentProfileUpdateRequest,
) -> DocumentProfile:
    file_asset = await get_owned_file(db, owner, file_id)
    profile = await db.scalar(select(DocumentProfile).where(DocumentProfile.owner_id == owner.id, DocumentProfile.file_id == file_asset.id))
    if profile is None:
        profile = DocumentProfile(owner_id=owner.id, file_id=file_asset.id, title=file_asset.display_name, document_type="general")
        db.add(profile)
        await db.flush()
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(profile, key, value)
    now = datetime.now(UTC)
    profile.confirmed_at = now
    latest_task = await db.scalar(
        select(DocumentIntelligenceTask)
        .where(DocumentIntelligenceTask.owner_id == owner.id, DocumentIntelligenceTask.file_id == file_asset.id)
        .order_by(DocumentIntelligenceTask.created_at.desc())
        .limit(1)
    )
    if latest_task:
        latest_task.confirmed_at = now
        if latest_task.status == "completed":
            latest_task.status = "confirmed"
    await write_profile_fields(db, profile, source="user", confirmed_at=now)
    await db.commit()
    await db.refresh(profile)
    return profile


async def retry_file_intelligence(db: AsyncSession, owner: User, file_id: UUID) -> DocumentIntelligenceTask:
    file_asset = await get_owned_file(db, owner, file_id)
    task = DocumentIntelligenceTask(owner_id=owner.id, file_id=file_asset.id, source_type=file_asset.file_category, status="pending")
    db.add(task)
    await db.flush()
    await enqueue_worker_task(
        db,
        task_type=DOCUMENT_EXTRACT_TASK_TYPE,
        owner_id=owner.id,
        target_type="document_intelligence_task",
        target_id=task.id,
        payload_json={"document_intelligence_task_id": str(task.id)},
    )
    await db.commit()
    await db.refresh(task)
    return task


async def enqueue_file_text_from_source_image_task(
    db: AsyncSession,
    *,
    owner: User,
    file_asset: FileAsset,
    source_image_asset: FileAsset,
) -> DocumentIntelligenceTask:
    task = DocumentIntelligenceTask(
        owner_id=owner.id,
        file_id=file_asset.id,
        source_type="document",
        status="pending",
        parsed_json={"source_image_file_id": str(source_image_asset.id)},
    )
    db.add(task)
    await db.flush()
    await enqueue_worker_task(
        db,
        task_type=DOCUMENT_EXTRACT_TASK_TYPE,
        owner_id=owner.id,
        target_type="document_intelligence_task",
        target_id=task.id,
        payload_json={"document_intelligence_task_id": str(task.id)},
    )
    return task


async def index_file_text_from_source_image(
    db: AsyncSession,
    *,
    owner: User,
    file_asset: FileAsset,
    source_image_asset: FileAsset,
    source_image_bytes: bytes,
) -> DocumentIntelligenceTask:
    task = DocumentIntelligenceTask(
        owner_id=owner.id,
        file_id=file_asset.id,
        source_type="document",
        status="processing",
    )
    db.add(task)
    await db.flush()
    try:
        from io import BytesIO

        from PIL import Image

        with Image.open(BytesIO(source_image_bytes)) as image:
            raw_text = extract_receipt_image_text(image).strip()
        if not raw_text:
            raise ValueError("No readable text found")
        detected_type, confidence = classify_document(raw_text, file_asset)
        parsed = parse_document_fields(raw_text, detected_type, file_asset)
        parsed["source_image_file_id"] = str(source_image_asset.id)
        task.raw_text = raw_text
        task.detected_type = detected_type
        task.confidence = confidence
        task.parsed_json = parsed
        task.status = "completed"
        task.finished_at = datetime.now(UTC)
        task.error_message = None
        await db.execute(delete(DocumentTextChunk).where(DocumentTextChunk.file_id == file_asset.id))
        for index, text_chunk in enumerate(chunk_text(raw_text)):
            db.add(
                DocumentTextChunk(
                    owner_id=owner.id,
                    file_id=file_asset.id,
                    task_id=task.id,
                    chunk_index=index,
                    page_number=None,
                    text=text_chunk,
                    created_at=datetime.now(UTC),
                )
            )
        await upsert_profile(db, task, file_asset, parsed)
    except Exception as exc:
        task.status = "failed"
        task.error_message = str(exc)
        task.finished_at = datetime.now(UTC)
    return task


async def process_document_extract_task(db: AsyncSession, worker_task: WorkerTask) -> None:
    task_id = UUID((worker_task.payload_json or {}).get("document_intelligence_task_id"))
    task = await db.get(DocumentIntelligenceTask, task_id)
    if task is None:
        raise AppError("document_intelligence_task_not_found", "Document intelligence task not found", 404)
    file_asset = await db.get(FileAsset, task.file_id)
    if file_asset is None or file_asset.is_deleted:
        raise AppError("document_intelligence_file_not_found", "File is no longer available", 404)
    try:
        task.status = "processing"
        raw_text = await _extract_text_for_document_task(db, task, file_asset)
        if not raw_text.strip():
            raise ValueError("No readable text found")
        detected_type, confidence = classify_document(raw_text, file_asset)
        parsed = parse_document_fields(raw_text, detected_type, file_asset)
        if task.parsed_json and task.parsed_json.get("source_image_file_id"):
            parsed["source_image_file_id"] = task.parsed_json["source_image_file_id"]
        owner = await db.get(User, task.owner_id)
        ai_parsed = await enhance_document_parse(raw_text, parsed, detected_type) if owner and owner.plan == "pro" else {}
        if ai_parsed:
            detected_type = ai_parsed.get("document_type") or detected_type
            parsed = {**parsed, **ai_parsed, "ai_enhanced": True}
        task.raw_text = raw_text
        task.detected_type = detected_type
        task.confidence = confidence
        task.parsed_json = parsed
        task.status = "completed"
        task.finished_at = datetime.now(UTC)
        task.error_message = None
        await db.execute(delete(DocumentTextChunk).where(DocumentTextChunk.file_id == file_asset.id))
        for index, text_chunk in enumerate(chunk_text(raw_text)):
            db.add(
                DocumentTextChunk(
                    owner_id=task.owner_id,
                    file_id=file_asset.id,
                    task_id=task.id,
                    chunk_index=index,
                    page_number=None,
                    text=text_chunk,
                    created_at=datetime.now(UTC),
                )
            )
        await upsert_profile(db, task, file_asset, parsed)
        await mark_task_completed(db, worker_task)
    except Exception as exc:
        message = str(exc)
        task.status = "failed"
        task.error_message = message
        task.finished_at = datetime.now(UTC)
        await mark_task_failed(db, worker_task, message)


async def _extract_text_for_document_task(db: AsyncSession, task: DocumentIntelligenceTask, file_asset: FileAsset) -> str:
    source_image_id = (task.parsed_json or {}).get("source_image_file_id")
    if source_image_id:
        source_asset = await db.get(FileAsset, UUID(source_image_id))
        if source_asset is None or source_asset.is_deleted:
            raise ValueError("Source image is no longer available")
        from io import BytesIO

        from PIL import Image

        with Image.open(BytesIO(decrypt_file_asset(source_asset))) as image:
            return extract_receipt_image_text(image).strip()
    return extract_text_from_bytes(file_asset, decrypt_file_asset(file_asset))


async def upsert_profile(db: AsyncSession, task: DocumentIntelligenceTask, file_asset: FileAsset, parsed: dict) -> DocumentProfile:
    profile = await db.scalar(select(DocumentProfile).where(DocumentProfile.file_id == file_asset.id))
    if profile is None:
        profile = DocumentProfile(owner_id=task.owner_id, file_id=file_asset.id)
        db.add(profile)
    profile.task_id = task.id
    profile.document_type = task.detected_type or "general"
    profile.title = parsed.get("title") or file_asset.display_name
    profile.summary = parsed.get("summary")
    profile.issuer = parsed.get("issuer")
    profile.counterparty = parsed.get("counterparty")
    profile.primary_date = parsed.get("primary_date")
    profile.amount = parsed.get("amount")
    profile.currency = parsed.get("currency")
    profile.warranty_until = parsed.get("warranty_until")
    profile.serial_number = parsed.get("serial_number")
    profile.keywords = parsed.get("keywords")
    profile.labels = parsed.get("labels")
    profile.ai_summary = parsed.get("summary") if parsed.get("ai_enhanced") else profile.ai_summary
    profile.ai_metadata = {"enabled": True, "model_source": "ollama"} if parsed.get("ai_enhanced") else None
    await db.flush()
    await write_profile_fields(db, profile, source="ai" if parsed.get("ai_enhanced") else "rules")
    return profile


async def write_profile_fields(
    db: AsyncSession,
    profile: DocumentProfile,
    *,
    source: str,
    confirmed_at: datetime | None = None,
) -> None:
    field_labels = {
        "document_type": "Document type",
        "title": "Title",
        "issuer": "Issuer",
        "counterparty": "Counterparty",
        "primary_date": "Date",
        "amount": "Amount",
        "currency": "Currency",
        "warranty_until": "Warranty until",
        "serial_number": "Serial number",
    }
    values = {
        "document_type": profile.document_type,
        "title": profile.title,
        "issuer": profile.issuer,
        "counterparty": profile.counterparty,
        "primary_date": profile.primary_date,
        "amount": profile.amount,
        "currency": profile.currency,
        "warranty_until": profile.warranty_until,
        "serial_number": profile.serial_number,
    }
    existing = {
        field.field_key: field
        for field in await db.scalars(select(DocumentFieldValue).where(DocumentFieldValue.profile_id == profile.id))
    }
    for key, value in values.items():
        if value in (None, ""):
            continue
        field = existing.get(key)
        if field is None:
            field = DocumentFieldValue(owner_id=profile.owner_id, file_id=profile.file_id, profile_id=profile.id, field_key=key)
            db.add(field)
        field.field_label = field_labels[key]
        field.field_value = str(value)
        field.confidence = 0.94 if source == "user" else 0.72
        field.source = source
        field.confirmed_at = confirmed_at
    await db.flush()


def classify_document(raw_text: str, file_asset: FileAsset) -> tuple[str, float]:
    lower = raw_text.lower()
    rules = [
        ("invoice", 0.86, ("invoice", "bill to", "due date", "invoice number")),
        ("receipt", 0.82, ("total", "subtotal", "tax", "receipt", "amount paid", "visa", "mastercard")),
        ("contract", 0.78, ("agreement", "party", "term", "whereas", "contract")),
        ("warranty", 0.8, ("warranty", "serial number", "model", "coverage", "limited warranty")),
        ("manual", 0.7, ("manual", "instructions", "installation", "troubleshooting")),
        ("statement", 0.76, ("statement", "account number", "opening balance", "closing balance")),
    ]
    for document_type, confidence, keywords in rules:
        if any(keyword in lower for keyword in keywords):
            return document_type, confidence
    if file_asset.file_category == "photo":
        return "general", 0.48
    if file_asset.file_category == "document":
        return "general", 0.58
    return "unknown", 0.35


def parse_document_fields(raw_text: str, detected_type: str, file_asset: FileAsset) -> dict:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    title = next((line[:180] for line in lines if len(line) > 2), file_asset.display_name)
    summary = " ".join(lines[:4])[:600] if lines else raw_text[:600]
    amount = None
    currency = None
    amount_match = re.search(r"(?P<marker>USD|CAD|CNY|RMB|\$)?\s*(?P<amount>\d{1,6}[,.]\d{2})", raw_text, re.IGNORECASE)
    if amount_match:
        amount = amount_match.group("amount").replace(",", ".")
        marker = amount_match.group("marker")
        currency = "CNY" if marker == "RMB" else marker or None
    date_match = re.search(r"(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]20\d{2}|20\d{2}年\d{1,2}月\d{1,2}日)", raw_text)
    due_match = re.search(r"(?i)(due date|expires?|valid until|warranty until)[:\s-]+([0-9]{4}[-/.][0-9]{1,2}[-/.][0-9]{1,2}|[0-9]{1,2}[-/.][0-9]{1,2}[-/.][0-9]{4})", raw_text)
    serial_match = re.search(r"(?i)(serial|s/n|sn|serial number|model)[:\s#-]+([A-Z0-9-]{4,})", raw_text)
    invoice_match = re.search(r"(?i)(invoice number|invoice no\.?|invoice #)[:\s#-]+([A-Z0-9-]{3,})", raw_text)
    counterparty = extract_labeled_value(raw_text, ("bill to", "customer", "party b", "buyer"))
    keywords = extract_keywords(raw_text)
    labels = [detected_type] + [keyword for keyword in keywords[:4] if keyword != detected_type]
    return {
        "title": f"Invoice {invoice_match.group(2)}" if invoice_match and detected_type == "invoice" else title,
        "summary": summary,
        "issuer": title if detected_type in {"receipt", "invoice", "warranty"} else None,
        "counterparty": counterparty,
        "primary_date": date_match.group(0).replace("/", "-").replace(".", "-") if date_match else None,
        "amount": amount,
        "currency": currency,
        "warranty_until": due_match.group(2).replace("/", "-").replace(".", "-") if due_match and detected_type == "warranty" else None,
        "serial_number": serial_match.group(2)[:120] if serial_match else None,
        "keywords": keywords,
        "labels": labels[:8],
        "raw_text_preview": raw_text[:800],
    }


def extract_labeled_value(raw_text: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        match = re.search(rf"(?im)^{re.escape(label)}[:\s-]+(.+)$", raw_text)
        if match:
            return match.group(1).strip()[:255]
    return None


def extract_keywords(raw_text: str) -> list[str]:
    words = re.findall(r"[A-Za-z\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff-]{2,}", raw_text.lower())
    stop = {"the", "and", "for", "with", "this", "that", "from", "your", "you", "are", "total", "date"}
    counts: dict[str, int] = {}
    for word in words:
        if word in stop:
            continue
        counts[word] = counts.get(word, 0) + 1
    return [word for word, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:12]]


def chunk_text(raw_text: str, *, max_chars: int = 1800) -> list[str]:
    text = re.sub(r"\s+", " ", raw_text).strip()
    if not text:
        return []
    return [text[index : index + max_chars] for index in range(0, len(text), max_chars)]
