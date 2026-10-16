from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.responses import success_response
from app.models.file_asset import FileAsset
from app.models.inbox_item import InboxItem
from app.models.user import User
from app.models.receipt import Receipt
from app.schemas.file_asset import FileAssetPublic
from app.schemas.inbox import InboxItemPublic, InboxResolveRequest
from app.services.important_doc_service import verify_vault_unlock_token
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
    x_vault_unlock: str | None = Header(default=None, alias="X-Vault-Unlock"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    if payload.action == "vault":
        await verify_vault_unlock_token(current_user, x_vault_unlock)
    item = await resolve_inbox_item(session, current_user, item_id, payload.action)
    file_asset = await session.get(FileAsset, item.file_id)
    data = _serialize(item, file_asset)
    if item.resolved_as == "receipt":
        # Lets the inbox offer "open it" right away.
        receipt_id = await session.scalar(select(Receipt.id).where(Receipt.owner_id == current_user.id, Receipt.file_id == item.file_id))
        data["receipt_id"] = str(receipt_id) if receipt_id else None
    return success_response(data)
