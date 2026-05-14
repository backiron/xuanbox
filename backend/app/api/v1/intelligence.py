from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.responses import success_response
from app.models.user import User
from app.schemas.document_intelligence import (
    DocumentIntelligenceBundle,
    DocumentFieldValuePublic,
    DocumentIntelligenceTaskPublic,
    DocumentProfilePublic,
    DocumentTextChunkPublic,
    DocumentProfileUpdateRequest,
)
from app.services.document_intelligence_service import get_file_intelligence, retry_file_intelligence, update_file_intelligence_profile

router = APIRouter()


@router.get("/files/{file_id}")
async def file_intelligence_endpoint(
    file_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    tasks, profile, fields, chunks = await get_file_intelligence(session, current_user, file_id)
    bundle = DocumentIntelligenceBundle(
        tasks=[DocumentIntelligenceTaskPublic.model_validate(task) for task in tasks],
        profile=DocumentProfilePublic.model_validate(profile) if profile else None,
        fields=[DocumentFieldValuePublic.model_validate(field) for field in fields],
        chunks=[DocumentTextChunkPublic.model_validate(chunk) for chunk in chunks],
    )
    return success_response(bundle.model_dump(mode="json"))


@router.post("/files/{file_id}/retry")
async def retry_file_intelligence_endpoint(
    file_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    task = await retry_file_intelligence(session, current_user, file_id)
    return success_response(DocumentIntelligenceTaskPublic.model_validate(task).model_dump(mode="json"))


@router.patch("/files/{file_id}/profile")
async def update_file_intelligence_profile_endpoint(
    file_id: UUID,
    payload: DocumentProfileUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    profile = await update_file_intelligence_profile(session, current_user, file_id, payload)
    return success_response(DocumentProfilePublic.model_validate(profile).model_dump(mode="json"))
