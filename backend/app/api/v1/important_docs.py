from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.http import attachment_headers
from app.core.responses import success_response
from app.models.user import User
from app.schemas.document import DocumentPublic
from app.schemas.important_doc import ImportantDocCreateRequest, VaultPinRequest, VaultStatus, VaultUnlockResponse
from app.services.important_doc_service import (
    VAULT_UNLOCK_SECONDS,
    create_important_doc_for_file,
    decrypt_important_doc,
    list_important_docs,
    remove_important_doc,
    setup_vault_pin,
    unlock_vault_pin,
    verify_vault_unlock_token,
)

router = APIRouter()


@router.get("/status")
async def important_docs_status(current_user: User = Depends(require_user_app)) -> dict:
    locked_until = current_user.vault_pin_locked_until.isoformat() if current_user.vault_pin_locked_until else None
    return success_response(VaultStatus(pin_set=bool(current_user.vault_pin_hash), locked_until=locked_until).model_dump())


@router.post("/setup")
async def setup_important_docs_pin(
    payload: VaultPinRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    token = await setup_vault_pin(session, current_user, payload.pin)
    return success_response(VaultUnlockResponse(unlock_token=token, expires_in_seconds=VAULT_UNLOCK_SECONDS).model_dump())


@router.post("/unlock")
async def unlock_important_docs_pin(
    payload: VaultPinRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    token = await unlock_vault_pin(session, current_user, payload.pin)
    return success_response(VaultUnlockResponse(unlock_token=token, expires_in_seconds=VAULT_UNLOCK_SECONDS).model_dump())


@router.get("")
async def list_important_docs_endpoint(
    x_vault_unlock: str | None = Header(default=None, alias="X-Vault-Unlock"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    verify_vault_unlock_token(current_user, x_vault_unlock)
    documents = await list_important_docs(session, current_user)
    return success_response([DocumentPublic.model_validate(document).model_dump(mode="json") for document in documents])


@router.post("/from-file/{file_id}")
async def create_important_doc_from_file_endpoint(
    file_id: UUID,
    payload: ImportantDocCreateRequest,
    x_vault_unlock: str | None = Header(default=None, alias="X-Vault-Unlock"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    verify_vault_unlock_token(current_user, x_vault_unlock)
    document = await create_important_doc_for_file(session, current_user, file_id, payload.to_document_create())
    return success_response(DocumentPublic.model_validate(document).model_dump(mode="json"))


@router.get("/{document_id}/download")
async def download_important_doc_endpoint(
    document_id: UUID,
    x_vault_unlock: str | None = Header(default=None, alias="X-Vault-Unlock"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> Response:
    verify_vault_unlock_token(current_user, x_vault_unlock)
    _, file_asset, plain_bytes = await decrypt_important_doc(session, current_user, document_id)
    headers = attachment_headers(file_asset.original_filename)
    return Response(content=plain_bytes, media_type=file_asset.mime_type or "application/octet-stream", headers=headers)


@router.delete("/{document_id}")
async def remove_important_doc_endpoint(
    document_id: UUID,
    x_vault_unlock: str | None = Header(default=None, alias="X-Vault-Unlock"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    verify_vault_unlock_token(current_user, x_vault_unlock)
    await remove_important_doc(session, current_user, document_id)
    return success_response(message="removed")
