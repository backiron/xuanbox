"""The vault (historically "Important docs"). Every item route needs a fresh unlock in X-Vault-Unlock."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.errors import AppError
from app.core.http import attachment_headers
from app.core.responses import success_response
from app.models.photo_asset import PhotoAsset
from app.models.user import User
from app.schemas.important_doc import VaultPinRequest, VaultStatus, VaultUnlockResponse
from app.services import important_doc_service as vault
from app.services.important_doc_service import VAULT_UNLOCK_SECONDS

router = APIRouter()


class VaultChangePinRequest(BaseModel):
    current_pin: str = Field(pattern=r"^\d{6}$")
    new_pin: str = Field(pattern=r"^\d{6}$")


class VaultResetPinRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)
    new_pin: str = Field(pattern=r"^\d{6}$")


class VaultAddRequest(BaseModel):
    title: str | None = Field(default=None, max_length=180)


class VaultItemUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=180)
    note: str | None = Field(default=None, max_length=2000)


def _unlocked(token: str) -> dict:
    return success_response(VaultUnlockResponse(unlock_token=token, expires_in_seconds=VAULT_UNLOCK_SECONDS).model_dump())


async def require_vault_unlock(
    x_vault_unlock: str | None = Header(default=None, alias="X-Vault-Unlock"),
    current_user: User = Depends(require_user_app),
) -> User:
    await vault.verify_vault_unlock_token(current_user, x_vault_unlock)
    return current_user


@router.get("/status")
async def vault_status(current_user: User = Depends(require_user_app)) -> dict:
    locked_until = vault._pin_locked_until(current_user)
    return success_response(VaultStatus(pin_set=bool(current_user.vault_pin_hash), locked_until=locked_until.isoformat() if locked_until else None).model_dump())


@router.post("/setup")
async def setup_vault_pin(payload: VaultPinRequest, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_user_app)) -> dict:
    return _unlocked(await vault.setup_vault_pin(session, current_user, payload.pin))


@router.post("/unlock")
async def unlock_vault(payload: VaultPinRequest, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_user_app)) -> dict:
    return _unlocked(await vault.unlock_vault_pin(session, current_user, payload.pin))


@router.post("/lock")
async def lock_vault(current_user: User = Depends(require_user_app)) -> dict:
    await vault.lock_vault(current_user)
    return success_response(message="locked")


@router.post("/change-pin")
async def change_vault_pin(payload: VaultChangePinRequest, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_user_app)) -> dict:
    return _unlocked(await vault.change_vault_pin(session, current_user, payload.current_pin, payload.new_pin))


@router.post("/reset-pin")
async def reset_vault_pin(payload: VaultResetPinRequest, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_user_app)) -> dict:
    return _unlocked(await vault.reset_vault_pin(session, current_user, payload.password, payload.new_pin))


@router.get("")
async def list_vault_items(session: AsyncSession = Depends(get_session), current_user: User = Depends(require_vault_unlock)) -> dict:
    return success_response(await vault.list_vault_items(session, current_user))


@router.post("/upload")
async def upload_to_vault(file: UploadFile = File(...), session: AsyncSession = Depends(get_session), current_user: User = Depends(require_vault_unlock)) -> dict:
    return success_response(await vault.upload_to_vault(session, current_user, file))


@router.post("/from-file/{file_id}")
async def add_file_to_vault(
    file_id: UUID,
    payload: VaultAddRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_vault_unlock),
) -> dict:
    return success_response(await vault.add_file_to_vault(session, current_user, file_id, payload.title if payload else None))


@router.post("/from-photo/{photo_id}")
async def add_photo_to_vault(photo_id: UUID, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_vault_unlock)) -> dict:
    file_id = await session.scalar(select(PhotoAsset.file_id).where(PhotoAsset.id == photo_id, PhotoAsset.owner_id == current_user.id))
    if file_id is None:
        raise AppError("photo_not_found", "Photo not found", 404)
    return success_response(await vault.add_file_to_vault(session, current_user, file_id))


@router.get("/{document_id}/content")
async def vault_item_content(
    document_id: UUID,
    download: bool = False,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_vault_unlock),
) -> Response:
    _, file_asset, plain_bytes = await vault.read_vault_item(session, current_user, document_id)
    mime_type = file_asset.mime_type or "application/octet-stream"
    if download or not vault.is_inline_type(mime_type):
        headers = attachment_headers(file_asset.original_filename)
    else:
        headers = {"Content-Disposition": "inline"}
    headers |= {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    return Response(content=plain_bytes, media_type=mime_type, headers=headers)


@router.get("/{document_id}/thumbnail")
async def vault_item_thumbnail(document_id: UUID, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_vault_unlock)) -> Response:
    content = await vault.vault_thumbnail(session, current_user, document_id)
    return Response(content=content, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.patch("/{document_id}")
async def update_vault_item(
    document_id: UUID,
    payload: VaultItemUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_vault_unlock),
) -> dict:
    return success_response(await vault.rename_vault_item(session, current_user, document_id, payload.title, payload.note))


@router.post("/{document_id}/restore")
async def restore_vault_item(document_id: UUID, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_vault_unlock)) -> dict:
    return success_response(await vault.remove_from_vault(session, current_user, document_id))


@router.delete("/{document_id}")
async def delete_vault_item(document_id: UUID, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_vault_unlock)) -> dict:
    await vault.delete_vault_item(session, current_user, document_id)
    return success_response(message="deleted")
