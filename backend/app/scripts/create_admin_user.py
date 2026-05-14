import asyncio
import os

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.services.audit_service import write_audit_log


async def main() -> None:
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ["ADMIN_PASSWORD"]
    email = os.environ.get("ADMIN_EMAIL", f"{username}@xuanbox.local")

    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(User).where(User.username == username))
        if existing:
            existing.email = email
            existing.password_hash = hash_password(password)
            existing.display_name = "Admin"
            existing.role = "owner"
            existing.plan = "pro"
            existing.status = "active"
            existing.storage_limit_bytes = None
            user = existing
            action = "admin.bootstrap.reset"
        else:
            user = User(
                username=username,
                email=email,
                password_hash=hash_password(password),
                display_name="Admin",
                role="owner",
                plan="pro",
                status="active",
                storage_limit_bytes=None,
            )
            db.add(user)
            action = "admin.bootstrap.create"

        await db.flush()
        await write_audit_log(db, action=action, actor_user_id=user.id, target_type="user", target_id=str(user.id))
        await db.commit()
        print(f"admin ready: {user.username} {user.role} {user.status}")


if __name__ == "__main__":
    asyncio.run(main())
