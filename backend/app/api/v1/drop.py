import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.errors import AppError
from app.core.http import attachment_headers
from app.core.responses import success_response
from app.core.security import decode_token
from app.models.user import User
from app.schemas.transfer import TransferItemPublic, TransferSaveRequest, TransferSessionCreateRequest, TransferSessionPublic
from app.services.transfer_service import (
    create_transfer_session,
    delete_transfer_item,
    download_transfer_item,
    get_owned_session,
    list_transfer_items,
    list_transfer_sessions,
    save_transfer_item,
    upload_transfer_item,
)

router = APIRouter()


def session_public(session, request: Request, token: str | None = None) -> dict:
    data = TransferSessionPublic.model_validate(session).model_dump(mode="json")
    public_token = token or session.public_token
    if public_token:
        upload_path = f"/drop/public/{public_token}"
        data["token"] = public_token
        data["public_token"] = public_token
        data["upload_url"] = str(request.base_url).rstrip("/") + upload_path
    return data


@router.get("/sessions")
async def list_sessions_endpoint(
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    sessions = await list_transfer_sessions(session, current_user)
    return success_response([session_public(item, request) for item in sessions])


@router.post("/sessions")
async def create_session_endpoint(
    payload: TransferSessionCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    transfer_session, token = await create_transfer_session(session, current_user, payload)
    return success_response(session_public(transfer_session, request, token))


@router.get("/sessions/{session_id}/items")
async def list_session_items_endpoint(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    items = await list_transfer_items(session, current_user, session_id)
    return success_response([TransferItemPublic.model_validate(item).model_dump(mode="json") for item in items])


@router.get("/sessions/{session_id}/events")
async def session_events_endpoint(
    session_id: UUID,
    access_token: str | None = Query(default=None),
    xb_drop_events_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    token = xb_drop_events_token or access_token
    if not token:
        raise AppError("not_authenticated", "Authentication required", 401)
    payload = decode_token(token)
    if payload.get("type") != "access" or not payload.get("sub"):
        raise AppError("invalid_token", "Invalid token", 401)
    current_user = await session.get(User, UUID(payload["sub"]))
    if current_user is None or current_user.status != "active":
        raise AppError("user_inactive", "User is inactive or does not exist", 401)
    await get_owned_session(session, current_user, session_id)

    async def event_stream():
        last_ids: set[str] | None = None
        while True:
            items = await list_transfer_items(session, current_user, session_id)
            current_ids = {str(item.id) for item in items}
            if current_ids != last_ids:
                payload = [TransferItemPublic.model_validate(item).model_dump(mode="json") for item in items]
                yield f"event: items\ndata: {json.dumps(payload, default=str)}\n\n"
                last_ids = current_ids
            else:
                yield "event: heartbeat\ndata: {}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/sessions/{session_id}/events-auth")
async def authorize_session_events_endpoint(
    session_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> Response:
    await get_owned_session(session, current_user, session_id)
    authorization = request.headers.get("authorization", "")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise AppError("not_authenticated", "Authentication required", 401)
    response = Response(
        content=json.dumps(success_response(message="events authorized")),
        media_type="application/json",
    )
    response.set_cookie(
        "xb_drop_events_token",
        token,
        max_age=15 * 60,
        httponly=True,
        samesite="lax",
        path=f"/api/v1/drop/sessions/{session_id}/events",
    )
    return response


@router.get("/items/{item_id}/download")
async def download_item_endpoint(
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> Response:
    item, plain_bytes = await download_transfer_item(session, current_user, item_id)
    headers = attachment_headers(item.original_filename)
    return Response(content=plain_bytes, media_type=item.mime_type or "application/octet-stream", headers=headers)


@router.delete("/items/{item_id}")
async def delete_item_endpoint(
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    await delete_transfer_item(session, current_user, item_id)
    return success_response(message="deleted")


@router.post("/items/{item_id}/save")
async def save_item_endpoint(
    item_id: UUID,
    payload: TransferSaveRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
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
