from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.errors import AppError
from app.core.security import decode_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise AppError("not_authenticated", "Authentication required", 401)

    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise AppError("invalid_token_type", "Invalid token type", 401)

    user_id = payload.get("sub")
    if not user_id:
        raise AppError("invalid_token", "Invalid token", 401)

    user = await session.get(User, UUID(user_id))
    if user is None or user.status != "active":
        raise AppError("user_inactive", "User is inactive or does not exist", 401)
    return user


def require_roles(*roles: str):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise AppError("permission_denied", "Permission denied", 403)
        return current_user

    return role_checker


require_owner = require_roles("owner")
require_admin = require_roles("owner", "admin")
