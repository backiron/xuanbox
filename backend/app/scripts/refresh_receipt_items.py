"""Re-read the item lines of existing receipts with the local AI (Pro accounts only).

Only the recognised item list (parsed_json items / items_summary) is updated; merchant, amount, dates and
the review status of each receipt are left exactly as they are. The search index is refreshed afterwards.
Usage: python -m app.scripts.refresh_receipt_items [--apply]
"""

import asyncio
import sys
import time

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import AsyncSessionLocal, engine
from app.core.redis import redis_client
from app.models.ocr_task import OcrTask
from app.models.receipt import Receipt
from app.models.user import User
from app.services.receipt_ai_service import enhance_receipt_parse
from app.services.search_index_service import index_receipt


async def main(apply: bool) -> None:
    started = time.monotonic()
    updated = 0
    async with AsyncSessionLocal() as db:
        receipts = list(await db.scalars(select(Receipt).join(User, User.id == Receipt.owner_id).where(User.plan == "pro")))
        for receipt in receipts:
            task = await db.scalar(
                select(OcrTask)
                .where(OcrTask.receipt_id == receipt.id, OcrTask.status.in_(("completed", "confirmed")))
                .order_by(OcrTask.created_at.desc())
                .limit(1)
            )
            if task is None or not task.raw_text:
                continue
            result = await enhance_receipt_parse(task.raw_text, task.parsed_json or {})
            items = result.get("items")
            print(f"{receipt.merchant or '?'}: {result.get('items_summary') or '(no items found)'}")
            if not items or not apply:
                continue
            parsed = dict(task.parsed_json or {})
            parsed["items"] = items
            parsed["items_summary"] = result["items_summary"]
            task.parsed_json = parsed
            flag_modified(task, "parsed_json")
            await db.flush()
            await index_receipt(db, receipt.id)
            await db.commit()
            updated += 1
    print(f"{len(receipts)} receipts, {updated} {'updated' if apply else 'would update (dry run)'}, {time.monotonic() - started:.0f}s")
    await engine.dispose()
    await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))
