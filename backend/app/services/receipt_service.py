from datetime import date
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.receipt import Receipt
from app.models.user import User
from app.schemas.receipt import ReceiptCreateRequest, ReceiptUpdateRequest
from app.services.audit_service import write_audit_log
from app.services.file_service import get_owned_file, upload_file


async def list_receipts(
    db: AsyncSession,
    owner: User,
    *,
    q: str | None = None,
    category: str | None = None,
    merchant: str | None = None,
    year: int | None = None,
) -> list[Receipt]:
    statement = select(Receipt).where(Receipt.owner_id == owner.id)
    if q:
        like = f"%{q}%"
        statement = statement.where(or_(Receipt.merchant.ilike(like), Receipt.category.ilike(like), Receipt.notes.ilike(like)))
    if category:
        statement = statement.where(Receipt.category == category)
    if merchant:
        statement = statement.where(Receipt.merchant.ilike(f"%{merchant}%"))
    if year:
        statement = statement.where(Receipt.purchase_date >= date(year, 1, 1), Receipt.purchase_date <= date(year, 12, 31))
    result = await db.scalars(statement.order_by(Receipt.purchase_date.desc().nullslast(), Receipt.created_at.desc()))
    return list(result)


async def create_receipt_from_upload(
    db: AsyncSession,
    owner: User,
    upload: UploadFile,
    payload: ReceiptCreateRequest,
) -> Receipt:
    file_asset = await upload_file(db, owner=owner, upload=upload, source="receipt_upload")
    receipt = Receipt(owner_id=owner.id, file_id=file_asset.id, **payload.model_dump())
    db.add(receipt)
    await db.flush()
    await write_audit_log(db, action="receipt.create", actor_user_id=owner.id, target_type="receipt", target_id=str(receipt.id))
    await db.commit()
    await db.refresh(receipt)
    return receipt


async def create_receipt_for_file(
    db: AsyncSession,
    owner: User,
    file_id: UUID,
    *,
    merchant: str | None = None,
    category: str | None = None,
) -> Receipt:
    await get_owned_file(db, owner, file_id)
    receipt = Receipt(owner_id=owner.id, file_id=file_id, merchant=merchant, category=category)
    db.add(receipt)
    await db.flush()
    await write_audit_log(db, action="receipt.create_from_file", actor_user_id=owner.id, target_type="file", target_id=str(file_id))
    await db.commit()
    await db.refresh(receipt)
    return receipt


async def update_receipt(db: AsyncSession, owner: User, receipt_id: UUID, payload: ReceiptUpdateRequest) -> Receipt:
    receipt = await db.scalar(select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == owner.id))
    if receipt is None:
        raise AppError("receipt_not_found", "Receipt not found", 404)
    for field, value in payload.model_dump().items():
        setattr(receipt, field, value)
    await write_audit_log(db, action="receipt.update", actor_user_id=owner.id, target_type="receipt", target_id=str(receipt.id))
    await db.commit()
    await db.refresh(receipt)
    return receipt
