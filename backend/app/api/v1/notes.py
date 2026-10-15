from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.responses import success_response
from app.models.user import User
from app.services import note_service

router = APIRouter()


class NoteCreateRequest(BaseModel):
    body: str = ""


class NoteUpdateRequest(BaseModel):
    body: str | None = None
    pinned: bool | None = None
    # When the client last loaded or saved this note; a newer server copy means another device edited it.
    base_updated_at: datetime | None = Field(default=None)


@router.get("")
async def list_notes_endpoint(q: str | None = None, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_user_app)) -> dict:
    return success_response(await note_service.list_notes(session, current_user, q))


@router.post("")
async def create_note_endpoint(payload: NoteCreateRequest, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_user_app)) -> dict:
    return success_response(await note_service.create_note(session, current_user, payload.body))


@router.get("/{note_id}")
async def get_note_endpoint(note_id: UUID, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_user_app)) -> dict:
    return success_response(await note_service.get_note(session, current_user, note_id))


@router.patch("/{note_id}")
async def update_note_endpoint(
    note_id: UUID,
    payload: NoteUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    note = await note_service.update_note(
        session, current_user, note_id, body=payload.body, pinned=payload.pinned, base_updated_at=payload.base_updated_at
    )
    return success_response(note)


@router.delete("/{note_id}")
async def delete_note_endpoint(note_id: UUID, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_user_app)) -> dict:
    await note_service.delete_note(session, current_user, note_id)
    return success_response({"deleted": True})


@router.post("/{note_id}/images")
async def add_note_image_endpoint(
    note_id: UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    return success_response(await note_service.add_image(session, current_user, note_id, file))


@router.get("/{note_id}/images/{image_id}")
async def note_image_endpoint(
    note_id: UUID,
    image_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> Response:
    content, mime_type = await note_service.read_image(session, current_user, note_id, image_id)
    return Response(content=content, media_type=mime_type, headers={"Cache-Control": "private, max-age=86400"})
