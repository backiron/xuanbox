import asyncio

from sqlalchemy import exists, select

from app.core.database import AsyncSessionLocal
from app.models.file_asset import FileAsset
from app.models.photo_asset import PhotoAsset
from app.models.user import User
from app.services.document_intelligence_service import enqueue_document_intelligence_task
from app.services.file_service import decrypt_file_asset
from app.services.photo_service import create_photo_record_for_asset


async def main() -> None:
    repaired = 0
    skipped = 0
    async with AsyncSessionLocal() as db:
        rows = list(
            await db.scalars(
                select(FileAsset)
                .where(
                    FileAsset.file_category == "photo",
                    FileAsset.is_deleted.is_(False),
                    FileAsset.source.not_in(["system_import", "avatar"]),
                    ~exists().where(PhotoAsset.file_id == FileAsset.id),
                )
                .order_by(FileAsset.created_at.asc())
            )
        )
        for file_asset in rows:
            owner = await db.get(User, file_asset.owner_id)
            if owner is None:
                skipped += 1
                continue
            try:
                plain_bytes = decrypt_file_asset(file_asset)
                await create_photo_record_for_asset(db, owner, file_asset, plain_bytes)
                await enqueue_document_intelligence_task(db, owner=owner, file_asset=file_asset, source_type="photo")
                repaired += 1
            except Exception:
                skipped += 1
        await db.commit()
    print(f"repaired={repaired} skipped={skipped}")


if __name__ == "__main__":
    asyncio.run(main())
