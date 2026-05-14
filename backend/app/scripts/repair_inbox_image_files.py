import asyncio

from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.file_asset import FileAsset
from app.models.inbox_item import InboxItem
from app.models.user import User
from app.services.inbox_service import create_pdf_file_from_image


async def main() -> None:
    repaired = 0
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(InboxItem, FileAsset, User)
            .join(FileAsset, FileAsset.id == InboxItem.file_id)
            .join(User, User.id == InboxItem.owner_id)
            .where(
                InboxItem.status == "saved",
                InboxItem.resolved_as == "file",
                FileAsset.mime_type.like("image/%"),
                FileAsset.source == "manual_upload",
            )
        )
        for inbox_item, image_asset, owner in rows.all():
            pdf_asset = await create_pdf_file_from_image(session, owner, image_asset)
            inbox_item.file_id = pdf_asset.id
            repaired += 1
        regenerated_rows = await session.execute(
            select(InboxItem, FileAsset, User)
            .join(FileAsset, FileAsset.id == InboxItem.file_id)
            .join(User, User.id == InboxItem.owner_id)
            .where(
                InboxItem.status == "saved",
                InboxItem.resolved_as == "file",
                FileAsset.mime_type == "text/markdown",
                FileAsset.source == "manual_upload",
            )
        )
        for inbox_item, markdown_asset, owner in regenerated_rows.all():
            stem = Path(markdown_asset.original_filename).stem
            image_asset = await session.scalar(
                select(FileAsset)
                .where(
                    FileAsset.owner_id == owner.id,
                    FileAsset.original_filename.in_([f"{stem}.jpg", f"{stem}.jpeg", f"{stem}.png", f"{stem}.webp"]),
                    FileAsset.mime_type.like("image/%"),
                    FileAsset.source == "inbox_upload",
                    FileAsset.is_deleted.is_(False),
                )
                .order_by(FileAsset.created_at.desc())
                .limit(1)
            )
            if image_asset is None:
                continue
            markdown_asset.is_deleted = True
            pdf_asset = await create_pdf_file_from_image(session, owner, image_asset)
            inbox_item.file_id = pdf_asset.id
            repaired += 1
        await session.commit()
    print(f"repaired={repaired}")


if __name__ == "__main__":
    asyncio.run(main())
