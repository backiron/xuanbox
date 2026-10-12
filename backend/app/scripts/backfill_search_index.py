"""Index existing receipts and documents of Pro accounts for meaning-based search.

Safe to re-run: unchanged items are skipped. Usage: python -m app.scripts.backfill_search_index
"""

import asyncio
import time

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.core.redis import redis_client
from app.models.document_intelligence import DocumentProfile, DocumentTextChunk
from app.models.receipt import Receipt
from app.models.user import User
from app.services.search_index_service import index_file, index_receipt


async def main() -> None:
    started = time.monotonic()
    counts: dict[str, int] = {}
    async with AsyncSessionLocal() as db:
        pro_users = select(User.id).where(User.plan == "pro")
        receipt_ids = list(await db.scalars(select(Receipt.id).where(Receipt.owner_id.in_(pro_users))))
        file_ids = set(await db.scalars(select(DocumentProfile.file_id).where(DocumentProfile.owner_id.in_(pro_users))))
        file_ids |= set(await db.scalars(select(DocumentTextChunk.file_id).where(DocumentTextChunk.owner_id.in_(pro_users))))
        for receipt_id in receipt_ids:
            outcome = await index_receipt(db, receipt_id)
            counts[f"receipt:{outcome}"] = counts.get(f"receipt:{outcome}", 0) + 1
            await db.commit()
        for file_id in file_ids:
            outcome = await index_file(db, file_id)
            counts[f"file:{outcome}"] = counts.get(f"file:{outcome}", 0) + 1
            await db.commit()
    print(counts, f"{time.monotonic() - started:.1f}s")
    await engine.dispose()
    await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
