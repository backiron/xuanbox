from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.core.responses import success_response
from app.models.user import User
from app.schemas.document import DocumentCreateRequest, DocumentPublic, DocumentUpdateRequest
from app.services.document_service import (
    create_document_for_file,
    create_document_from_upload,
    decrypt_document,
    list_documents,
    list_expiring_documents,
    update_document,
)

router = APIRouter()


@router.get("")
async def list_documents_endpoint(
    q: str | None = None,
    document_type: str | None = None,
    security_level: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    documents = await list_documents(session, current_user, q=q, document_type=document_type, security_level=security_level)
    return success_response([DocumentPublic.model_validate(document).model_dump(mode="json") for document in documents])


@router.get("/reminders")
async def document_reminders_endpoint(
    days: int = 90,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    documents = await list_expiring_documents(session, current_user, days=days)
    return success_response([DocumentPublic.model_validate(document).model_dump(mode="json") for document in documents])


@router.post("/upload")
async def upload_document_endpoint(
    file: UploadFile = File(...),
    document_type: str = Form(default="contract"),
    title: str = Form(...),
    issuer: str | None = Form(default=None),
    issued_date: date | None = Form(default=None),
    expires_at: date | None = Form(default=None),
    note: str | None = Form(default=None),
    security_level: str = Form(default="normal"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    payload = DocumentCreateRequest(
        document_type=document_type,
        title=title,
        issuer=issuer,
        issued_date=issued_date,
        expires_at=expires_at,
        note=note,
        security_level=security_level,
    )
    document = await create_document_from_upload(session, current_user, file, payload)
    return success_response(DocumentPublic.model_validate(document).model_dump(mode="json"))


@router.post("/from-file/{file_id}")
async def create_document_for_file_endpoint(
    file_id: UUID,
    payload: DocumentCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    document = await create_document_for_file(session, current_user, file_id, payload)
    return success_response(DocumentPublic.model_validate(document).model_dump(mode="json"))


@router.patch("/{document_id}")
async def update_document_endpoint(
    document_id: UUID,
    payload: DocumentUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    document = await update_document(session, current_user, document_id, payload)
    return success_response(DocumentPublic.model_validate(document).model_dump(mode="json"))


@router.get("/{document_id}/download")
async def download_document_endpoint(
    document_id: UUID,
    password: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    _, file_asset, plain_bytes = await decrypt_document(session, current_user, document_id, password=password)
    headers = {"Content-Disposition": f'attachment; filename="{file_asset.original_filename}"'}
    return Response(content=plain_bytes, media_type=file_asset.mime_type or "application/octet-stream", headers=headers)
