from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_admin
from app.core.responses import success_response
from app.models.user import User
from app.schemas.invite import InviteCreateRequest, InvitePublic
from app.services.invite_service import create_invite, list_invites

router = APIRouter()


@router.post("")
async def create_invite_endpoint(
    payload: InviteCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    invite = await create_invite(session, payload, current_user)
    return success_response(InvitePublic.model_validate(invite).model_dump(mode="json"))


@router.get("")
async def list_invites_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    invites = await list_invites(session, current_user)
    return success_response([InvitePublic.model_validate(invite).model_dump(mode="json") for invite in invites])
