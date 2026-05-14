from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.responses import success_response
from app.models.user import User
from app.services.search_service import search_all

router = APIRouter()


@router.get("")
async def search_endpoint(
    q: str = "",
    limit: int = 40,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    response = await search_all(session, current_user, q, limit=max(1, min(limit, 80)))
    return success_response(response.model_dump(mode="json"))
