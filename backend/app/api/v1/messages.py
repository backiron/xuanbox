from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_admin, require_user_app
from app.core.responses import success_response
from app.models.user import User
from app.schemas.message import MessageCreateRequest, MessagePublic
from app.services.message_service import (
    archive_admin_message,
    create_message,
    list_admin_messages,
    list_user_messages,
    mark_read,
    unread_count,
)

router = APIRouter()
admin_router = APIRouter()


@router.get("")
async def list_messages_endpoint(
    unread_only: bool = False,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    messages = await list_user_messages(session, current_user, unread_only=unread_only)
    return success_response([MessagePublic.model_validate(message).model_dump(mode="json") for message in messages])


@router.get("/unread-count")
async def unread_count_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    return success_response({"unread_count": await unread_count(session, current_user)})


@router.post("/{message_id}/read")
async def mark_read_endpoint(
    message_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    message = await mark_read(session, current_user, message_id)
    return success_response(MessagePublic.model_validate(message).model_dump(mode="json"))


@admin_router.get("")
async def admin_list_messages_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    messages = await list_admin_messages(session)
    return success_response([MessagePublic.model_validate(message).model_dump(mode="json") for message in messages])


@admin_router.post("")
async def admin_create_message_endpoint(
    payload: MessageCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    message = await create_message(session, current_user, payload)
    return success_response(MessagePublic.model_validate(message).model_dump(mode="json"))


@admin_router.delete("/{message_id}")
async def admin_archive_message_endpoint(
    message_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    await archive_admin_message(session, current_user, message_id)
    return success_response(message="archived")
