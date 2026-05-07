from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.core.responses import success_response
from app.models.user import User
from app.schemas.transfer import TransferItemPublic, TransferSaveRequest, TransferSessionCreateRequest, TransferSessionPublic
from app.services.transfer_service import (
    create_transfer_session,
    list_transfer_items,
    list_transfer_sessions,
    save_transfer_item,
    upload_transfer_item,
)

router = APIRouter()


def session_public(session, request: Request, token: str | None = None) -> dict:
    data = TransferSessionPublic.model_validate(session).model_dump(mode="json")
    if token:
        upload_path = f"/drop/public/{token}"
        data["token"] = token
        data["upload_url"] = str(request.base_url).rstrip("/") + upload_path
    return data


@router.get("/sessions")
async def list_sessions_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    sessions = await list_transfer_sessions(session, current_user)
    return success_response([TransferSessionPublic.model_validate(item).model_dump(mode="json") for item in sessions])


@router.post("/sessions")
async def create_session_endpoint(
    payload: TransferSessionCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    transfer_session, token = await create_transfer_session(session, current_user, payload)
    return success_response(session_public(transfer_session, request, token))


@router.get("/sessions/{session_id}/items")
async def list_session_items_endpoint(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    items = await list_transfer_items(session, current_user, session_id)
    return success_response([TransferItemPublic.model_validate(item).model_dump(mode="json") for item in items])


@router.post("/items/{item_id}/save")
async def save_item_endpoint(
    item_id: UUID,
    payload: TransferSaveRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    item = await save_transfer_item(session, current_user, item_id, payload)
    return success_response(TransferItemPublic.model_validate(item).model_dump(mode="json"))


@router.post("/public/{token}/upload")
async def public_upload_endpoint(
    token: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    item = await upload_transfer_item(session, token, file)
    return success_response(TransferItemPublic.model_validate(item).model_dump(mode="json"))
