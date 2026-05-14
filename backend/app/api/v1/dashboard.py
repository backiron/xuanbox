from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.responses import success_response
from app.models.user import User
from app.services.dashboard_service import dashboard_summary

router = APIRouter()


@router.get("")
async def dashboard_summary_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    summary = await dashboard_summary(session, current_user)
    return success_response(summary.model_dump(mode="json"))
