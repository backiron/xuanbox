from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.responses import success_response
from app.models.user import User
from app.schemas.file_asset import FileAssetPublic
from app.services.file_service import list_trash

router = APIRouter()


@router.get("")
async def list_trash_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    files = await list_trash(session, current_user)
    return success_response([FileAssetPublic.model_validate(file).model_dump(mode="json") for file in files])
