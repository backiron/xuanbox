from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_asset import DocumentAsset
from app.models.file_asset import FileAsset
from app.models.photo_asset import PhotoAsset
from app.models.receipt import Receipt
from app.models.user import User
from app.schemas.dashboard import DashboardMetrics, DashboardSummary, ExpiringDocument


async def dashboard_summary(db: AsyncSession, owner: User) -> DashboardSummary:
    today = date.today()
    until = today + timedelta(days=90)
    storage_bytes = await db.scalar(
        select(func.coalesce(func.sum(FileAsset.file_size), 0)).where(FileAsset.owner_id == owner.id, FileAsset.is_deleted.is_(False))
    )
    photos_count = await db.scalar(select(func.count(PhotoAsset.id)).where(PhotoAsset.owner_id == owner.id))
    files_count = await db.scalar(
        select(func.count(FileAsset.id)).where(
            FileAsset.owner_id == owner.id,
            FileAsset.is_deleted.is_(False),
            FileAsset.source.not_in(["system_import", "avatar", "inbox_upload"]),
            FileAsset.file_category != "photo",
        )
    )
    receipts_count = await db.scalar(select(func.count(Receipt.id)).where(Receipt.owner_id == owner.id))
    pending_ocr_count = await db.scalar(
        select(func.count(Receipt.id)).where(Receipt.owner_id == owner.id, Receipt.ocr_status.in_(("pending", "processing", "completed", "failed")))
    )
    documents_count = await db.scalar(select(func.count(DocumentAsset.id)).where(DocumentAsset.owner_id == owner.id))
    expiring_result = await db.scalars(
        select(DocumentAsset)
        .where(DocumentAsset.owner_id == owner.id, DocumentAsset.expires_at.is_not(None))
        .where(DocumentAsset.expires_at >= today, DocumentAsset.expires_at <= until)
        .order_by(DocumentAsset.expires_at.asc())
        .limit(8)
    )
    return DashboardSummary(
        metrics=DashboardMetrics(
            storage_bytes=int(storage_bytes or 0),
            storage_limit_bytes=owner.storage_limit_bytes,
            photos_count=int(photos_count or 0),
            files_count=int(files_count or 0),
            receipts_count=int(receipts_count or 0),
            documents_count=int(documents_count or 0),
            pending_ocr_count=int(pending_ocr_count or 0),
        ),
        expiring_documents=[
            ExpiringDocument(
                id=document.id,
                title=document.title,
                document_type=document.document_type,
                issuer=document.issuer,
                expires_at=document.expires_at,
                security_level=document.security_level,
            )
            for document in expiring_result
            if document.expires_at is not None
        ],
    )
