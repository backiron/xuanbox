from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.responses import success_response
from app.models.user import User
from app.schemas.tag import TagAttachRequest, TagCreateRequest, TagLinkPublic, TagPublic, TagUpdateRequest
from app.services.tag_service import attach_tag, create_tag, list_tag_links, list_tags, update_tag

router = APIRouter()


@router.get("")
async def list_tags_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    tags = await list_tags(session, current_user)
    return success_response([TagPublic.model_validate(tag).model_dump(mode="json") for tag in tags])


@router.get("/links")
async def list_tag_links_endpoint(
    target_type: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    links = await list_tag_links(session, current_user, target_type)
    return success_response([TagLinkPublic.model_validate(link).model_dump(mode="json") for link in links])


@router.post("")
async def create_tag_endpoint(
    payload: TagCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    tag = await create_tag(session, current_user, payload)
    return success_response(TagPublic.model_validate(tag).model_dump(mode="json"))


@router.patch("/{tag_id}")
async def update_tag_endpoint(
    tag_id: UUID,
    payload: TagUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    tag = await update_tag(session, current_user, tag_id, payload)
    return success_response(TagPublic.model_validate(tag).model_dump(mode="json"))


@router.post("/{tag_id}/attach")
async def attach_tag_endpoint(
    tag_id: UUID,
    payload: TagAttachRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    await attach_tag(session, current_user, tag_id, payload)
    return success_response(message="attached")
