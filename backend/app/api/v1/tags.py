from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.core.responses import success_response
from app.models.user import User
from app.schemas.tag import TagAttachRequest, TagCreateRequest, TagPublic
from app.services.tag_service import attach_tag, create_tag, list_tags

router = APIRouter()


@router.get("")
async def list_tags_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    tags = await list_tags(session, current_user)
    return success_response([TagPublic.model_validate(tag).model_dump(mode="json") for tag in tags])


@router.post("")
async def create_tag_endpoint(
    payload: TagCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    tag = await create_tag(session, current_user, payload)
    return success_response(TagPublic.model_validate(tag).model_dump(mode="json"))


@router.post("/{tag_id}/attach")
async def attach_tag_endpoint(
    tag_id: UUID,
    payload: TagAttachRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    await attach_tag(session, current_user, tag_id, payload)
    return success_response(message="attached")
