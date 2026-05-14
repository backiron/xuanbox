from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.responses import success_response
from app.models.file_asset import FileAsset
from app.models.inbox_item import InboxItem
from app.models.user import User
from app.schemas.file_asset import FileAssetPublic
from app.schemas.inbox import InboxItemPublic, InboxResolveRequest
from app.services.inbox_service import list_inbox_items, resolve_inbox_item, upload_inbox_item

router = APIRouter()


def _serialize(item: InboxItem, file_asset: FileAsset | None = None) -> dict:
    data = InboxItemPublic.model_validate(item).model_dump(mode="json")
    if file_asset is not None:
        data["file"] = FileAssetPublic.model_validate(file_asset).model_dump(mode="json")
    return data


@router.post("/upload")
async def upload_inbox_endpoint(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    item = await upload_inbox_item(session, current_user, file)
    file_asset = await session.get(FileAsset, item.file_id)
    return success_response(_serialize(item, file_asset))


@router.get("")
async def list_inbox_endpoint(
    status: str = "pending",
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    rows = await list_inbox_items(session, current_user, status=status)
    return success_response([_serialize(item, file_asset) for item, file_asset in rows])


@router.post("/{item_id}/resolve")
async def resolve_inbox_endpoint(
    item_id: UUID,
    payload: InboxResolveRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    item = await resolve_inbox_item(session, current_user, item_id, payload.action)
    file_asset = await session.get(FileAsset, item.file_id)
    return success_response(_serialize(item, file_asset))
