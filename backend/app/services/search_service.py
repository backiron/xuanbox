from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_asset import DocumentAsset
from app.models.document_intelligence import DocumentFieldValue, DocumentProfile, DocumentTextChunk
from app.models.file_asset import FileAsset
from app.models.photo_asset import PhotoAsset
from app.models.receipt import Receipt
from app.models.user import User
from app.schemas.search import SearchResult, SearchResponse


def _snippet(text: str | None, query: str, *, limit: int = 220) -> str | None:
    if not text:
        return None
    lower = text.lower()
    index = lower.find(query.lower())
    if index < 0:
        return text[:limit]
    start = max(0, index - 70)
    end = min(len(text), index + len(query) + 140)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def _add_result(results: dict[tuple[str, UUID, str], SearchResult], result: SearchResult) -> None:
    key = (result.type, result.id, result.source)
    existing = results.get(key)
    if existing is None or result.score > existing.score:
        results[key] = result


async def search_all(db: AsyncSession, owner: User, query: str, *, limit: int = 40) -> SearchResponse:
    q = query.strip()
    if not q:
        return SearchResponse(query=q, results=[])
    like = f"%{q}%"
    results: dict[tuple[str, UUID, str], SearchResult] = {}
    vault_file_ids = select(DocumentAsset.file_id).where(
        DocumentAsset.owner_id == owner.id,
        DocumentAsset.security_level == "vault_locked",
    )

    file_rows = await db.scalars(
        select(FileAsset)
        .where(
            FileAsset.owner_id == owner.id,
            FileAsset.is_deleted.is_(False),
            FileAsset.source.not_in(["system_import", "avatar", "inbox_upload"]),
            FileAsset.id.not_in(vault_file_ids),
            or_(
                FileAsset.display_name.ilike(like),
                FileAsset.original_filename.ilike(like),
                FileAsset.mime_type.ilike(like),
                FileAsset.file_ext.ilike(like),
            ),
        )
        .order_by(FileAsset.updated_at.desc())
        .limit(limit)
    )
    for file_asset in file_rows:
        result_type = "photo" if file_asset.file_category == "photo" else "file"
        _add_result(
            results,
            SearchResult(
                type=result_type,
                id=file_asset.id,
                file_id=file_asset.id,
                title=file_asset.display_name,
                subtitle=file_asset.mime_type or file_asset.file_category,
                snippet=file_asset.original_filename,
                route="/photos" if result_type == "photo" else "/files",
                source="filename",
                score=90,
            ),
        )

    photo_rows = await db.execute(
        select(PhotoAsset, FileAsset)
        .join(FileAsset, FileAsset.id == PhotoAsset.file_id)
        .where(
            PhotoAsset.owner_id == owner.id,
            FileAsset.is_deleted.is_(False),
            FileAsset.source != "inbox_upload",
            or_(FileAsset.display_name.ilike(like), FileAsset.original_filename.ilike(like)),
        )
        .limit(limit)
    )
    for photo, file_asset in photo_rows.all():
        _add_result(
            results,
            SearchResult(
                type="photo",
                id=photo.id,
                file_id=file_asset.id,
                title=file_asset.display_name,
                subtitle=f"{photo.width or '?'} x {photo.height or '?'}",
                snippet=file_asset.original_filename,
                route="/photos",
                source="photo",
                score=88,
            ),
        )

    receipt_rows = await db.scalars(
        select(Receipt)
        .where(
            Receipt.owner_id == owner.id,
            or_(Receipt.merchant.ilike(like), Receipt.category.ilike(like), Receipt.notes.ilike(like)),
        )
        .limit(limit)
    )
    for receipt in receipt_rows:
        _add_result(
            results,
            SearchResult(
                type="receipt",
                id=receipt.id,
                file_id=receipt.file_id,
                title=receipt.merchant or "Receipt",
                subtitle=receipt.category or receipt.currency,
                snippet=receipt.notes,
                route="/receipts",
                source="receipt-fields",
                score=85,
            ),
        )

    document_rows = await db.scalars(
        select(DocumentAsset)
        .where(
            DocumentAsset.owner_id == owner.id,
            DocumentAsset.security_level != "vault_locked",
            or_(DocumentAsset.title.ilike(like), DocumentAsset.issuer.ilike(like), DocumentAsset.note.ilike(like), DocumentAsset.document_type.ilike(like)),
        )
        .limit(limit)
    )
    for document in document_rows:
        _add_result(
            results,
            SearchResult(
                type="document",
                id=document.id,
                file_id=document.file_id,
                title=document.title,
                subtitle=document.document_type,
                snippet=document.note or document.issuer,
                route="/files",
                source="document-fields",
                score=86,
            ),
        )

    profile_rows = await db.scalars(
        select(DocumentProfile)
        .join(FileAsset, FileAsset.id == DocumentProfile.file_id)
        .where(
            DocumentProfile.owner_id == owner.id,
            FileAsset.source != "inbox_upload",
            FileAsset.is_deleted.is_(False),
            or_(
                DocumentProfile.title.ilike(like),
                DocumentProfile.summary.ilike(like),
                DocumentProfile.issuer.ilike(like),
                DocumentProfile.counterparty.ilike(like),
                DocumentProfile.document_type.ilike(like),
                DocumentProfile.serial_number.ilike(like),
                DocumentProfile.ai_summary.ilike(like),
            ),
        )
        .limit(limit)
    )
    for profile in profile_rows:
        _add_result(
            results,
            SearchResult(
                type="intelligence",
                id=profile.id,
                file_id=profile.file_id,
                title=profile.title or "Recognized document",
                subtitle=profile.document_type,
                snippet=_snippet(profile.summary or profile.ai_summary, q),
                route="/files",
                source="profile",
                score=78,
            ),
        )

    field_rows = await db.scalars(
        select(DocumentFieldValue)
        .join(FileAsset, FileAsset.id == DocumentFieldValue.file_id)
        .where(
            DocumentFieldValue.owner_id == owner.id,
            FileAsset.source != "inbox_upload",
            FileAsset.is_deleted.is_(False),
            or_(DocumentFieldValue.field_label.ilike(like), DocumentFieldValue.field_value.ilike(like)),
        )
        .limit(limit)
    )
    for field in field_rows:
        _add_result(
            results,
            SearchResult(
                type="intelligence",
                id=field.id,
                file_id=field.file_id,
                title=field.field_label or field.field_key,
                subtitle="Structured field",
                snippet=_snippet(field.field_value, q),
                route="/files",
                source="profile",
                score=76,
            ),
        )

    chunk_rows = await db.scalars(
        select(DocumentTextChunk)
        .join(FileAsset, FileAsset.id == DocumentTextChunk.file_id)
        .where(
            DocumentTextChunk.owner_id == owner.id,
            FileAsset.source != "inbox_upload",
            FileAsset.is_deleted.is_(False),
            DocumentTextChunk.text.ilike(like),
        )
        .order_by(DocumentTextChunk.created_at.desc())
        .limit(limit)
    )
    for chunk in chunk_rows:
        _add_result(
            results,
            SearchResult(
                type="ocr",
                id=chunk.id,
                file_id=chunk.file_id,
                title="Text match",
                subtitle="Extracted text",
                snippet=_snippet(chunk.text, q),
                route="/files",
                source="ocr-text",
                score=72,
            ),
        )

    ordered = sorted(results.values(), key=lambda item: item.score, reverse=True)[:limit]
    return SearchResponse(query=q, results=ordered)
