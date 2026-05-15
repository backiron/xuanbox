from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.file_asset import FileAsset
from app.models.inbox_item import InboxItem
from app.models.user import User
from app.services.audit_service import write_audit_log
from app.services.file_service import create_encrypted_asset_from_bytes, decrypt_file_asset, get_owned_file
from app.services.ocr_service import create_receipt_ocr_task
from app.services.receipt_service import create_receipt_for_file
from app.services.upload_limits import read_user_upload_bytes


def _suggest_type(file_asset: FileAsset) -> tuple[str, str]:
    if file_asset.mime_type and file_asset.mime_type.startswith("image/"):
        return "photo", "Image upload. Save as photo, receipt, or a PDF file with searchable OCR text."
    if file_asset.file_category == "document":
        return "file", "Document-like upload. Save it to Files when it belongs in the vault."
    return "file", "General upload. Save it to Files or dismiss it after review."


async def upload_inbox_item(db: AsyncSession, owner: User, upload: UploadFile) -> InboxItem:
    plain_bytes = await read_user_upload_bytes(upload)

    file_asset = await create_encrypted_asset_from_bytes(
        db,
        owner=owner,
        plain_bytes=plain_bytes,
        original_filename=upload.filename or str(uuid4()),
        mime_type=upload.content_type,
        source="inbox_upload",
    )
    suggested_type, suggestion_reason = _suggest_type(file_asset)
    inbox_item = InboxItem(
        owner_id=owner.id,
        file_id=file_asset.id,
        status="pending",
        source="dashboard_upload",
        suggested_type=suggested_type,
        suggestion_reason=suggestion_reason,
    )
    db.add(inbox_item)

    if not (file_asset.mime_type or "").startswith("image/"):
        from app.services.document_intelligence_service import enqueue_document_intelligence_task

        await enqueue_document_intelligence_task(db, owner=owner, file_asset=file_asset, source_type=file_asset.file_category)
    await write_audit_log(
        db,
        action="inbox.upload",
        actor_user_id=owner.id,
        target_type="file",
        target_id=str(file_asset.id),
        metadata_json={"filename": file_asset.original_filename, "size": file_asset.file_size},
    )
    await db.commit()
    await db.refresh(inbox_item)
    return inbox_item


async def list_inbox_items(db: AsyncSession, owner: User, status: str = "pending") -> list[tuple[InboxItem, FileAsset]]:
    statement = (
        select(InboxItem, FileAsset)
        .join(FileAsset, FileAsset.id == InboxItem.file_id)
        .where(InboxItem.owner_id == owner.id, FileAsset.is_deleted.is_(False))
        .order_by(InboxItem.created_at.desc())
    )
    if status != "all":
        statement = statement.where(InboxItem.status == status)
    rows = await db.execute(statement)
    return list(rows.all())


async def get_owned_inbox_item(db: AsyncSession, owner: User, item_id: UUID) -> tuple[InboxItem, FileAsset]:
    row = await db.execute(
        select(InboxItem, FileAsset)
        .join(FileAsset, FileAsset.id == InboxItem.file_id)
        .where(InboxItem.id == item_id, InboxItem.owner_id == owner.id, FileAsset.is_deleted.is_(False))
    )
    result = row.first()
    if result is None:
        raise AppError("inbox_item_not_found", "Inbox item not found", 404)
    return result


async def resolve_inbox_item(db: AsyncSession, owner: User, item_id: UUID, action: str) -> InboxItem:
    inbox_item, file_asset = await get_owned_inbox_item(db, owner, item_id)
    if inbox_item.status != "pending":
        raise AppError("inbox_item_resolved", "Inbox item has already been resolved", 400)

    if action == "dismiss":
        inbox_item.status = "dismissed"
        inbox_item.resolved_as = "dismissed"
        inbox_item.resolved_at = datetime.now(UTC)
        await write_audit_log(db, action="inbox.dismiss", actor_user_id=owner.id, target_type="inbox", target_id=str(item_id))
        await db.commit()
        await db.refresh(inbox_item)
        return inbox_item

    if action == "file":
        if (file_asset.mime_type or "").startswith("image/"):
            file_asset = await create_pdf_file_from_image(db, owner, file_asset)
            inbox_item.file_id = file_asset.id
        else:
            file_asset.source = "manual_upload"
            if file_asset.file_category == "photo":
                file_asset.file_category = "document"
        resolved_as = "file"
    elif action == "photo":
        if not (file_asset.mime_type or "").startswith("image/"):
            raise AppError("invalid_photo", "Only image uploads can be saved as photos", 400)
        from app.services.photo_service import create_photo_record_for_asset

        await create_photo_record_for_asset(db, owner, file_asset, decrypt_file_asset(file_asset))
        file_asset.source = "manual_upload"
        file_asset.file_category = "photo"
        resolved_as = "photo"
    elif action == "receipt":
        file_asset.source = "manual_upload"
        if file_asset.file_category == "photo":
            file_asset.file_category = "document"
        receipt = await create_receipt_for_file(db, owner, file_asset.id)
        await create_receipt_ocr_task(db, owner, receipt.id)
        resolved_as = "receipt"
    else:
        raise AppError("invalid_inbox_action", "Unsupported inbox action", 400)

    inbox_item.status = "saved"
    inbox_item.resolved_as = resolved_as
    inbox_item.resolved_at = datetime.now(UTC)
    await write_audit_log(
        db,
        action=f"inbox.resolve.{resolved_as}",
        actor_user_id=owner.id,
        target_type="inbox",
        target_id=str(item_id),
        metadata_json={"file_id": str(file_asset.id)},
    )
    await db.commit()
    await db.refresh(inbox_item)
    return inbox_item


async def create_pdf_file_from_image(db: AsyncSession, owner: User, image_asset: FileAsset) -> FileAsset:
    stem = Path(image_asset.original_filename).stem or "scanned-document"
    image_bytes = decrypt_file_asset(image_asset)
    pdf_bytes = _image_bytes_to_pdf(image_bytes)
    pdf_asset = await create_encrypted_asset_from_bytes(
        db,
        owner=owner,
        plain_bytes=pdf_bytes,
        original_filename=f"{stem}.pdf",
        mime_type="application/pdf",
        source="manual_upload",
        file_category="document",
    )
    from app.services.document_intelligence_service import enqueue_file_text_from_source_image_task

    await enqueue_file_text_from_source_image_task(
        db,
        owner=owner,
        file_asset=pdf_asset,
        source_image_asset=image_asset,
    )

    image_asset.source = "inbox_upload"
    image_asset.file_category = "photo"
    await write_audit_log(
        db,
        action="inbox.image_to_pdf",
        actor_user_id=owner.id,
        target_type="file",
        target_id=str(pdf_asset.id),
        metadata_json={"source_image_file_id": str(image_asset.id)},
    )
    return pdf_asset


async def create_markdown_file_from_image(db: AsyncSession, owner: User, image_asset: FileAsset) -> FileAsset:
    # Backward-compatible alias for older repair scripts.
    return await create_pdf_file_from_image(db, owner, image_asset)


def _image_bytes_to_pdf(image_bytes: bytes) -> bytes:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            normalized = ImageOps.exif_transpose(image)
            if normalized.mode in {"RGBA", "LA"}:
                background = Image.new("RGB", normalized.size, "white")
                alpha = normalized.getchannel("A")
                background.paste(normalized.convert("RGB"), mask=alpha)
                normalized = background
            else:
                normalized = normalized.convert("RGB")
            output = BytesIO()
            normalized.save(output, format="PDF", resolution=150.0)
            return output.getvalue()
    except UnidentifiedImageError as exc:
        raise AppError("invalid_image", "Image could not be converted to PDF", 400) from exc
