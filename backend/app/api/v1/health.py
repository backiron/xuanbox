from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from app.core.redis import redis_client
from app.core.responses import success_response

router = APIRouter()


@router.get("")
async def health_check() -> dict:
    database_status = "ok"
    redis_status = "ok"

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"

    try:
        await redis_client.ping()
    except Exception:
        redis_status = "error"

    overall_status = "ok" if database_status == "ok" and redis_status == "ok" else "degraded"

    return success_response(
        data={
            "status": overall_status,
            "api": "ok",
            "database": database_status,
            "redis": redis_status,
        }
    )
