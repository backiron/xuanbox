from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session, require_user_app
from app.core.http import attachment_headers
from app.core.responses import success_response
from app.models.user import User
from app.schemas.share import PublicShareMetadata, ShareCreateRequest, SharePasswordRequest, SharePasswordResponse, SharePublic, ShareUpdateRequest
from app.services.share_service import (
    archive_inactive_shares,
    archive_share,
    create_share,
    deactivate_share,
    download_public_share,
    get_owned_share,
    get_public_share,
    list_created_shares,
    list_received_shares,
    public_share_metadata,
    target_name,
    update_share,
    create_share_access_token,
    SHARE_ACCESS_SECONDS,
    verify_share_password,
    write_share_access_log,
)

router = APIRouter()
public_router = APIRouter()


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def _share_public(db: AsyncSession, share) -> dict:
    payload = SharePublic.model_validate(share).model_dump(mode="json")
    payload["target_name"] = await target_name(db, share)
    payload["requires_password"] = bool(share.password_hash)
    return payload


@router.post("")
async def create_share_endpoint(
    payload: ShareCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    share = await create_share(session, current_user, payload)
    return success_response(await _share_public(session, share))


@router.get("")
async def list_shares_endpoint(
    mode: str = "created",
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    if mode == "received":
        shares = await list_received_shares(session, current_user)
    else:
        shares = await list_created_shares(session, current_user, archived=mode == "archived")
    return success_response([await _share_public(session, share) for share in shares])


@router.get("/{share_id}")
async def get_share_endpoint(
    share_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    share = await get_owned_share(session, current_user, share_id)
    return success_response(await _share_public(session, share))


@router.patch("/{share_id}")
async def update_share_endpoint(
    share_id: UUID,
    payload: ShareUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    share = await update_share(session, current_user, share_id, payload)
    return success_response(await _share_public(session, share))


@router.delete("/{share_id}")
async def delete_share_endpoint(
    share_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    await deactivate_share(session, current_user, share_id)
    return success_response(message="deactivated")


@router.post("/archive-inactive")
async def archive_inactive_shares_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    count = await archive_inactive_shares(session, current_user)
    return success_response({"count": count}, message="archived")


@router.delete("/{share_id}/archive")
async def archive_share_endpoint(
    share_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user_app),
) -> dict:
    await archive_share(session, current_user, share_id)
    return success_response(message="archived")


@public_router.get("/{token}")
async def public_share_endpoint(
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    share = await get_public_share(session, token, action="share.view", ip_address=_client_ip(request), user_agent=request.headers.get("user-agent"))
    name, file_asset = await public_share_metadata(session, share)
    owner = await session.get(User, share.owner_id)
    await write_share_access_log(
        session,
        share,
        action="share.view",
        success=True,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    payload = PublicShareMetadata(
        target_type=share.target_type,
        target_name=name,
        permission=share.permission,
        mime_type=file_asset.mime_type if file_asset else None,
        file_size=file_asset.file_size if file_asset else None,
        max_downloads=share.max_downloads,
        download_count=share.download_count,
        expires_at=share.expires_at,
        requires_password=bool(share.password_hash),
        owner_name=owner.display_name or owner.username if owner else "XuanBox user",
    )
    return success_response(payload.model_dump(mode="json"))


@public_router.post("/{token}/verify-password")
async def verify_public_share_password_endpoint(
    token: str,
    payload: SharePasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    share = await get_public_share(session, token, action="password.verify", ip_address=_client_ip(request), user_agent=request.headers.get("user-agent"))
    await verify_share_password(session, share, payload.password, ip_address=_client_ip(request), user_agent=request.headers.get("user-agent"))
    await write_share_access_log(
        session,
        share,
        action="password.verify",
        success=True,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    token = create_share_access_token(share)
    return success_response(SharePasswordResponse(access_token=token, expires_in_seconds=SHARE_ACCESS_SECONDS).model_dump())


@public_router.get("/{token}/download")
async def download_public_share_endpoint(
    token: str,
    request: Request,
    password: str | None = None,
    access_token: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> Response:
    header_token = request.headers.get("x-share-access")
    share = await get_public_share(session, token, action="share.download", ip_address=_client_ip(request), user_agent=request.headers.get("user-agent"))
    file_asset, plain_bytes = await download_public_share(
        session,
        share,
        password=password,
        access_token=header_token or access_token,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    headers = attachment_headers(file_asset.original_filename)
    return Response(content=plain_bytes, media_type=file_asset.mime_type or "application/octet-stream", headers=headers)
