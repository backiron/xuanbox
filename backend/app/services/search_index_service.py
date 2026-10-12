"""Meaning-based search over a user's own receipts and documents.

Text that already exists (receipt fields, OCR text, document profiles and text chunks) is turned into a
vector once by a local Ollama embedding model; a query is embedded and compared with the owner's own
vectors. Photos are never indexed, and only Pro accounts use it (the same on-demand rule as other AI).
"""

import asyncio
import hashlib
import json
import time
from urllib import request
from uuid import UUID

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document_asset import DocumentAsset
from app.models.document_intelligence import DocumentProfile, DocumentTextChunk
from app.models.file_asset import FileAsset
from app.models.ocr_task import OcrTask
from app.models.receipt import Receipt
from app.models.search_embedding import SearchEmbedding
from app.models.user import User
from app.services.ai_health_service import record_ai_result

SEARCH_INDEX_TASK_TYPE = "search_index"
MAX_CHUNKS_PER_FILE = 24
MAX_CHUNK_CHARS = 1500
# Calibrated with bge-m3 on real receipts: a real match stands clearly above the owner's typical score
# (the median over their items), and close runners-up are kept.
MIN_LIFT_OVER_MEDIAN = 0.04
RUNNER_UP_WINDOW = 0.06
SMALL_COLLECTION = 6
SMALL_COLLECTION_MIN = 0.5
MAX_RESULTS = 5


def search_ai_available(user: User | None) -> bool:
    return bool(settings.SEARCH_AI_ENABLED and user is not None and user.plan == "pro")


def _embed_sync(texts: list[str]) -> list[list[float]]:
    body = json.dumps({"model": settings.SEARCH_AI_MODEL, "input": texts}).encode("utf-8")
    http_request = request.Request(
        f"{settings.DOCUMENT_AI_BASE_URL.rstrip('/')}/api/embed",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(http_request, timeout=max(settings.DOCUMENT_AI_TIMEOUT_SECONDS, 30)) as response:
        return json.loads(response.read().decode("utf-8"))["embeddings"]


async def embed(texts: list[str], kind: str = "embedding") -> list[np.ndarray] | None:
    started = time.monotonic()
    try:
        vectors = await asyncio.to_thread(_embed_sync, texts)
    except Exception as exc:
        await record_ai_result(kind, False, time.monotonic() - started, f"{type(exc).__name__}: {exc}")
        return None
    await record_ai_result(kind, True, time.monotonic() - started)
    result = []
    for vector in vectors:
        array = np.asarray(vector, dtype=np.float32)
        norm = float(np.linalg.norm(array)) or 1.0
        result.append(array / norm)
    return result


async def _receipt_texts(db: AsyncSession, receipt: Receipt) -> list[str]:
    """What the purchase was, in plain words.

    Measured on real receipts: label templates ("Merchant: ...") and full OCR text (addresses, totals,
    card numbers) make every receipt look alike to the model; merchant, category and items separate them.
    """
    task = await db.scalar(
        select(OcrTask)
        .where(OcrTask.receipt_id == receipt.id, OcrTask.status.in_(("completed", "confirmed")))
        .order_by(OcrTask.created_at.desc())
        .limit(1)
    )
    parsed = (task.parsed_json or {}) if task else {}
    parts = [receipt.merchant, receipt.category, parsed.get("items_summary"), receipt.notes]
    text = ". ".join(str(part).strip() for part in parts if part and str(part).strip())
    if not text and task is not None:
        # Nothing recognised yet: a short OCR excerpt is better than no entry at all.
        text = (task.raw_text or "")[:300].strip()
    return [text] if text else []


async def _file_texts(db: AsyncSession, file_id: UUID) -> list[str]:
    profile = await db.scalar(select(DocumentProfile).where(DocumentProfile.file_id == file_id))
    file_asset = await db.get(FileAsset, file_id)
    head = [file_asset.display_name if file_asset else None]
    if profile is not None:
        head += [
            profile.document_type if profile.document_type not in ("general", "other") else None,
            profile.title,
            profile.ai_summary or profile.summary,
            profile.issuer,
            ", ".join(profile.keywords) if isinstance(profile.keywords, list) else None,
        ]
    chunks = list(
        await db.scalars(
            select(DocumentTextChunk.text)
            .where(DocumentTextChunk.file_id == file_id)
            .order_by(DocumentTextChunk.page_number.nulls_first(), DocumentTextChunk.chunk_index)
            .limit(MAX_CHUNKS_PER_FILE)
        )
    )
    texts = [". ".join(str(part).strip() for part in head if part and str(part).strip())]
    texts += [text[:MAX_CHUNK_CHARS] for text in chunks if text and text.strip()]
    return texts if profile is not None or chunks else []


async def _store(db: AsyncSession, owner_id: UUID, file_id: UUID, source_type: str, source_id: UUID, texts: list[str]) -> str:
    existing = list(await db.scalars(select(SearchEmbedding).where(SearchEmbedding.source_type == source_type, SearchEmbedding.source_id == source_id)))
    hashes = [hashlib.sha256(f"{settings.SEARCH_AI_MODEL}\n{text}".encode("utf-8")).hexdigest() for text in texts]
    if [row.content_hash for row in sorted(existing, key=lambda row: row.chunk_index)] == hashes:
        return "unchanged"
    vectors = await embed(texts, "search_index") if texts else []
    if vectors is None:
        raise RuntimeError("Embedding model unavailable")
    await db.execute(delete(SearchEmbedding).where(SearchEmbedding.source_type == source_type, SearchEmbedding.source_id == source_id))
    for index, (text, digest, vector) in enumerate(zip(texts, hashes, vectors)):
        db.add(
            SearchEmbedding(
                owner_id=owner_id,
                file_id=file_id,
                source_type=source_type,
                source_id=source_id,
                chunk_index=index,
                text=text,
                content_hash=digest,
                model=settings.SEARCH_AI_MODEL,
                vector=vector.astype(np.float32).tobytes(),
            )
        )
    await db.flush()
    return "indexed"


async def index_receipt(db: AsyncSession, receipt_id: UUID) -> str:
    receipt = await db.get(Receipt, receipt_id)
    owner = await db.get(User, receipt.owner_id) if receipt else None
    if receipt is None or not search_ai_available(owner):
        await db.execute(delete(SearchEmbedding).where(SearchEmbedding.source_type == "receipt", SearchEmbedding.source_id == receipt_id))
        return "removed"
    return await _store(db, receipt.owner_id, receipt.file_id, "receipt", receipt.id, await _receipt_texts(db, receipt))


async def index_file(db: AsyncSession, file_id: UUID) -> str:
    file_asset = await db.get(FileAsset, file_id)
    owner = await db.get(User, file_asset.owner_id) if file_asset else None
    vault = await db.scalar(select(DocumentAsset.id).where(DocumentAsset.file_id == file_id, DocumentAsset.security_level == "vault_locked"))
    # A receipt's file is indexed once, as the receipt (it carries the confirmed fields).
    is_receipt = await db.scalar(select(Receipt.id).where(Receipt.file_id == file_id).limit(1))
    if file_asset is None or file_asset.is_deleted or vault or is_receipt or not search_ai_available(owner):
        await db.execute(delete(SearchEmbedding).where(SearchEmbedding.source_type == "file", SearchEmbedding.source_id == file_id))
        return "removed"
    return await _store(db, file_asset.owner_id, file_id, "file", file_id, await _file_texts(db, file_id))


async def enqueue_search_index(db: AsyncSession, owner: User | None, source_type: str, source_id: UUID) -> None:
    """Queue (re)indexing after text changed. Cheap no-op for accounts without AI search."""
    if not search_ai_available(owner):
        return
    from app.models.worker_task import WorkerTask
    from app.services.worker_service import enqueue_worker_task

    pending = await db.scalar(
        select(WorkerTask.id).where(
            WorkerTask.task_type == SEARCH_INDEX_TASK_TYPE,
            WorkerTask.target_id == source_id,
            WorkerTask.status == "pending",
        )
    )
    if pending:
        return
    await enqueue_worker_task(
        db,
        task_type=SEARCH_INDEX_TASK_TYPE,
        owner_id=owner.id,
        target_type=source_type,
        target_id=source_id,
        payload_json={"source_type": source_type, "source_id": str(source_id)},
    )


async def process_search_index_task(db: AsyncSession, task) -> None:
    from app.services.worker_service import mark_task_completed

    payload = task.payload_json or {}
    source_id = UUID(payload["source_id"])
    if payload.get("source_type") == "receipt":
        await index_receipt(db, source_id)
    else:
        await index_file(db, source_id)
    await mark_task_completed(db, task)


async def semantic_search(db: AsyncSession, owner: User, query: str, *, limit: int = 10) -> list[dict]:
    """Best matches by meaning among the owner's own vectors, one per receipt or file."""
    if not search_ai_available(owner) or not query.strip():
        return []
    rows = (
        await db.execute(
            select(SearchEmbedding.source_type, SearchEmbedding.source_id, SearchEmbedding.file_id, SearchEmbedding.text, SearchEmbedding.vector).where(
                SearchEmbedding.owner_id == owner.id, SearchEmbedding.model == settings.SEARCH_AI_MODEL
            )
        )
    ).all()
    if not rows:
        return []
    vectors = await embed([query.strip()], "search_query")
    if not vectors:
        return []
    matrix = np.frombuffer(b"".join(row.vector for row in rows), dtype=np.float32).reshape(len(rows), -1)
    scores = matrix @ vectors[0]
    # One result per underlying file; a receipt wins over the same file's document entry.
    best: dict[UUID, tuple[float, object]] = {}
    for row, score in zip(rows, scores):
        current = best.get(row.file_id)
        if current is None or (row.source_type == "receipt", score) > (current[1].source_type == "receipt", current[0]):
            best[row.file_id] = (float(score), row)
    ranked = sorted(best.values(), key=lambda item: item[0], reverse=True)
    if not ranked:
        return []
    median = float(np.median([score for score, _row in ranked]))
    floor = max(ranked[0][0] - RUNNER_UP_WINDOW, median + MIN_LIFT_OVER_MEDIAN)
    if len(ranked) < SMALL_COLLECTION:
        # Too few items for a meaningful median.
        floor = max(floor, SMALL_COLLECTION_MIN)
    matches = [{"score": score, "source_type": row.source_type, "source_id": row.source_id, "file_id": row.file_id, "text": row.text} for score, row in ranked if score >= floor]
    return matches[: min(limit, MAX_RESULTS)]
