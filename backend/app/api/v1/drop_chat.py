import asyncio
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.dependencies import get_current_user_payload, get_session, require_user_app
from app.core.errors import AppError
from app.core.http import attachment_headers
from app.core.realtime import (
    PRESENCE_TTL_SECONDS,
    issue_ws_ticket,
    mark_device_offline,
    mark_device_online,
    publish_to_users,
    redeem_ws_ticket,
    user_channel,
)
from app.core.redis import redis_client
from app.core.responses import success_response
from app.models.auth_session import AuthSession
from app.models.device import Device
from app.models.user import User
from app.schemas.drop import (
    DropContactRequest,
    DropDeviceRenameRequest,
    DropDirectThreadRequest,
    DropSaveRequest,
    DropTextMessageRequest,
    DropUploadStartRequest,
)
from app.services import drop_service

router = APIRouter()

# A socket is closed after this long so the client reconnects with a fresh ticket, which re-checks the session.
WS_MAX_LIFETIME_SECONDS = 30 * 60


@dataclass
class DropActor:
    user: User
    device_id: UUID | None


async def get_drop_actor(
    current: tuple[User, dict] = Depends(get_current_user_payload),
    session: AsyncSession = Depends(get_session),
) -> DropActor:
    user = await require_user_app(current)
    session_id = current[1].get("session_id")
    auth_session = await session.get(AuthSession, UUID(session_id)) if session_id else None
    if auth_session is None or auth_session.owner_id != user.id or not auth_session.is_active or auth_session.revoked_at is not None:
        raise AppError("session_revoked", "This session has been signed out", 401)
    return DropActor(user=user, device_id=auth_session.device_id)


# ---------------------------------------------------------------- devices


@router.get("/me")
async def drop_me_endpoint(actor: DropActor = Depends(get_drop_actor), session: AsyncSession = Depends(get_session)) -> dict:
    devices = await drop_service.list_my_devices(session, actor.user, actor.device_id)
    return success_response(
        {
            "user": {"id": str(actor.user.id), "username": actor.user.username, "display_name": actor.user.display_name or actor.user.username},
            "current_device_id": str(actor.device_id) if actor.device_id else None,
            "devices": devices,
        }
    )


@router.patch("/devices/{device_id}")
async def rename_device_endpoint(
    device_id: UUID,
    payload: DropDeviceRenameRequest,
    actor: DropActor = Depends(get_drop_actor),
    session: AsyncSession = Depends(get_session),
) -> dict:
    device = await drop_service.rename_device(session, actor.user, device_id, payload.device_name)
    return success_response({"id": str(device.id), "device_name": device.device_name})


@router.delete("/devices/{device_id}")
async def remove_device_endpoint(device_id: UUID, actor: DropActor = Depends(get_drop_actor), session: AsyncSession = Depends(get_session)) -> dict:
    await drop_service.remove_device(session, actor.user, device_id, actor.device_id)
    return success_response(message="device removed")


# ---------------------------------------------------------------- contacts


@router.get("/contacts")
async def list_contacts_endpoint(actor: DropActor = Depends(get_drop_actor), session: AsyncSession = Depends(get_session)) -> dict:
    return success_response(await drop_service.list_contacts(session, actor.user))


@router.post("/contacts")
async def request_contact_endpoint(
    payload: DropContactRequest,
    actor: DropActor = Depends(get_drop_actor),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return success_response(await drop_service.request_contact(session, actor.user, payload.identifier))


@router.post("/contacts/{contact_id}/accept")
async def accept_contact_endpoint(contact_id: UUID, actor: DropActor = Depends(get_drop_actor), session: AsyncSession = Depends(get_session)) -> dict:
    return success_response(await drop_service.respond_contact(session, actor.user, contact_id, accept=True))


@router.post("/contacts/{contact_id}/decline")
async def decline_contact_endpoint(contact_id: UUID, actor: DropActor = Depends(get_drop_actor), session: AsyncSession = Depends(get_session)) -> dict:
    return success_response(await drop_service.respond_contact(session, actor.user, contact_id, accept=False))


@router.delete("/contacts/{contact_id}")
async def remove_contact_endpoint(contact_id: UUID, actor: DropActor = Depends(get_drop_actor), session: AsyncSession = Depends(get_session)) -> dict:
    await drop_service.remove_contact(session, actor.user, contact_id)
    return success_response(message="contact removed")


# ---------------------------------------------------------------- threads and messages


@router.get("/threads")
async def list_threads_endpoint(actor: DropActor = Depends(get_drop_actor), session: AsyncSession = Depends(get_session)) -> dict:
    return success_response(await drop_service.list_threads(session, actor.user, actor.device_id))


@router.post("/threads/direct")
async def open_direct_thread_endpoint(
    payload: DropDirectThreadRequest,
    actor: DropActor = Depends(get_drop_actor),
    session: AsyncSession = Depends(get_session),
) -> dict:
    thread = await drop_service.open_direct_thread(session, actor.user, payload.user_id)
    return success_response({"id": str(thread.id), "kind": thread.kind})


@router.get("/threads/{thread_id}/messages")
async def list_messages_endpoint(
    thread_id: UUID,
    before: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=drop_service.MAX_PAGE_SIZE),
    actor: DropActor = Depends(get_drop_actor),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return success_response(await drop_service.list_messages(session, actor.user, thread_id, before=before, limit=limit))


@router.post("/threads/{thread_id}/messages")
async def send_text_endpoint(
    thread_id: UUID,
    payload: DropTextMessageRequest,
    actor: DropActor = Depends(get_drop_actor),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return success_response(await drop_service.send_text(session, actor.user, actor.device_id, thread_id, payload))


@router.post("/threads/{thread_id}/files")
async def send_file_endpoint(
    thread_id: UUID,
    file: UploadFile = File(...),
    target_device_id: UUID | None = Form(default=None),
    client_id: str | None = Form(default=None, max_length=64),
    actor: DropActor = Depends(get_drop_actor),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return success_response(
        await drop_service.send_file(
            session,
            actor.user,
            actor.device_id,
            thread_id,
            file,
            target_device_id=target_device_id,
            client_id=client_id,
        )
    )


@router.post("/threads/{thread_id}/uploads")
async def start_upload_endpoint(
    thread_id: UUID,
    payload: DropUploadStartRequest,
    actor: DropActor = Depends(get_drop_actor),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return success_response(
        await drop_service.start_upload(
            session,
            actor.user,
            actor.device_id,
            thread_id,
            filename=payload.filename,
            mime_type=payload.mime_type,
            file_size=payload.file_size,
            target_device_id=payload.target_device_id,
            client_id=payload.client_id,
        )
    )


@router.get("/uploads/{upload_id}")
async def upload_status_endpoint(upload_id: UUID, actor: DropActor = Depends(get_drop_actor), session: AsyncSession = Depends(get_session)) -> dict:
    return success_response(await drop_service.upload_status(session, actor.user, upload_id))


@router.put("/uploads/{upload_id}/chunks/{index}")
async def upload_chunk_endpoint(
    upload_id: UUID,
    index: int,
    request: Request,
    actor: DropActor = Depends(get_drop_actor),
    session: AsyncSession = Depends(get_session),
) -> dict:
    limit = settings.DROP_CHUNK_SIZE_MB * 1024 * 1024
    declared = int(request.headers.get("content-length") or 0)
    if declared > limit:
        raise AppError("upload_chunk_size", "Chunk is too large", 413)
    data = await request.body()
    if len(data) > limit:
        raise AppError("upload_chunk_size", "Chunk is too large", 413)
    return success_response(await drop_service.put_chunk(session, actor.user, upload_id, index, data))


@router.post("/uploads/{upload_id}/complete")
async def complete_upload_endpoint(upload_id: UUID, actor: DropActor = Depends(get_drop_actor), session: AsyncSession = Depends(get_session)) -> dict:
    return success_response(await drop_service.complete_upload(session, actor.user, upload_id))


@router.delete("/uploads/{upload_id}")
async def cancel_upload_endpoint(upload_id: UUID, actor: DropActor = Depends(get_drop_actor), session: AsyncSession = Depends(get_session)) -> dict:
    await drop_service.cancel_upload(session, actor.user, upload_id)
    return success_response(message="cancelled")


@router.post("/threads/{thread_id}/read")
async def mark_read_endpoint(thread_id: UUID, actor: DropActor = Depends(get_drop_actor), session: AsyncSession = Depends(get_session)) -> dict:
    last_read_at = await drop_service.mark_thread_read(session, actor.user, thread_id)
    return success_response({"last_read_at": last_read_at})


def _file_response(message, chunks) -> StreamingResponse:
    headers = attachment_headers(message.filename or "file")
    headers["Content-Length"] = str(message.file_size or 0)
    headers["Cache-Control"] = "private, no-store"
    return StreamingResponse(chunks, media_type=message.mime_type or "application/octet-stream", headers=headers)


@router.get("/messages/{message_id}/download")
async def download_message_endpoint(message_id: UUID, actor: DropActor = Depends(get_drop_actor), session: AsyncSession = Depends(get_session)) -> StreamingResponse:
    message, chunks = await drop_service.download_message_file(session, actor.user, message_id)
    return _file_response(message, chunks)


@router.post("/messages/{message_id}/download-link")
async def download_link_endpoint(message_id: UUID, actor: DropActor = Depends(get_drop_actor), session: AsyncSession = Depends(get_session)) -> dict:
    token = await drop_service.create_download_link(session, actor.user, message_id)
    return success_response({"url": f"/api/v1/drop/messages/{message_id}/file?token={token}", "expires_in_seconds": drop_service.DOWNLOAD_LINK_SECONDS})


@router.get("/messages/{message_id}/file")
async def download_by_link_endpoint(message_id: UUID, token: str = Query(...), session: AsyncSession = Depends(get_session)) -> StreamingResponse:
    message, chunks = await drop_service.download_with_token(session, message_id, token)
    return _file_response(message, chunks)


@router.get("/messages/{message_id}/thumbnail")
async def message_thumbnail_endpoint(message_id: UUID, actor: DropActor = Depends(get_drop_actor), session: AsyncSession = Depends(get_session)) -> Response:
    content = await drop_service.read_message_thumbnail(session, actor.user, message_id)
    return Response(content=content, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})


@router.post("/messages/{message_id}/save")
async def save_message_endpoint(
    message_id: UUID,
    payload: DropSaveRequest,
    actor: DropActor = Depends(get_drop_actor),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return success_response(await drop_service.save_message_to_library(session, actor.user, message_id, payload))


@router.delete("/messages/{message_id}")
async def delete_message_endpoint(message_id: UUID, actor: DropActor = Depends(get_drop_actor), session: AsyncSession = Depends(get_session)) -> dict:
    await drop_service.delete_message(session, actor.user, message_id)
    return success_response(message="deleted")


# ---------------------------------------------------------------- realtime


@router.post("/ws-ticket")
async def ws_ticket_endpoint(actor: DropActor = Depends(get_drop_actor)) -> dict:
    ticket = await issue_ws_ticket({"user_id": str(actor.user.id), "device_id": str(actor.device_id) if actor.device_id else ""})
    return success_response({"ticket": ticket, "ping_interval_seconds": PRESENCE_TTL_SECONDS // 3})


async def _touch_device(device_id: str) -> None:
    async with AsyncSessionLocal() as db:
        device = await db.get(Device, UUID(device_id))
        if device is not None:
            device.last_seen_at = datetime.now(UTC)
            await db.commit()


@router.websocket("/ws")
async def drop_websocket(websocket: WebSocket, ticket: str = Query(...)) -> None:
    claims = await redeem_ws_ticket(ticket)
    if not claims:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    user_id = claims["user_id"]
    device_id = claims.get("device_id") or None
    connection_id = secrets.token_hex(8)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(user_channel(user_id))

    if device_id:
        await mark_device_online(device_id, connection_id)
        await _touch_device(device_id)
        await publish_to_users([user_id], "presence", {"device_id": device_id, "online": True})

    async def forward_events() -> None:
        async for item in pubsub.listen():
            if item.get("type") == "message":
                await websocket.send_text(item["data"])

    async def receive_pings() -> None:
        while True:
            await websocket.receive_text()
            if device_id:
                await mark_device_online(device_id, connection_id)
            await websocket.send_text(json.dumps({"event": "pong"}))

    tasks = [
        asyncio.create_task(forward_events()),
        asyncio.create_task(receive_pings()),
        asyncio.create_task(asyncio.sleep(WS_MAX_LIFETIME_SECONDS)),
    ]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    except WebSocketDisconnect:
        pass
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await pubsub.unsubscribe()
        await pubsub.aclose()
        if device_id and await mark_device_offline(device_id, connection_id):
            await publish_to_users([user_id], "presence", {"device_id": device_id, "online": False})
        try:
            await websocket.close(code=4000)
        except RuntimeError:
            pass
