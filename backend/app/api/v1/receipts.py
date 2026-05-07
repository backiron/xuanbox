from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.core.responses import success_response
from app.models.user import User
from app.schemas.receipt import ReceiptCreateRequest, ReceiptPublic, ReceiptUpdateRequest
from app.services.receipt_service import create_receipt_from_upload, list_receipts, update_receipt

router = APIRouter()


@router.get("")
async def list_receipts_endpoint(
    q: str | None = None,
    category: str | None = None,
    merchant: str | None = None,
    year: int | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    receipts = await list_receipts(session, current_user, q=q, category=category, merchant=merchant, year=year)
    return success_response([ReceiptPublic.model_validate(receipt).model_dump(mode="json") for receipt in receipts])


@router.post("/upload")
async def upload_receipt_endpoint(
    file: UploadFile = File(...),
    merchant: str | None = Form(default=None),
    category: str | None = Form(default=None),
    amount: Decimal | None = Form(default=None),
    currency: str = Form(default="USD"),
    purchase_date: date | None = Form(default=None),
    warranty_until: date | None = Form(default=None),
    notes: str | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    payload = ReceiptCreateRequest(
        merchant=merchant,
        category=category,
        amount=amount,
        currency=currency,
        purchase_date=purchase_date,
        warranty_until=warranty_until,
        notes=notes,
    )
    receipt = await create_receipt_from_upload(session, current_user, file, payload)
    return success_response(ReceiptPublic.model_validate(receipt).model_dump(mode="json"))


@router.patch("/{receipt_id}")
async def update_receipt_endpoint(
    receipt_id: UUID,
    payload: ReceiptUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    receipt = await update_receipt(session, current_user, receipt_id, payload)
    return success_response(ReceiptPublic.model_validate(receipt).model_dump(mode="json"))
