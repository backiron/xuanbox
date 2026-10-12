"""One-off: copy recognised values into receipts that are waiting for review (ocr_status == "completed").

Only empty fields are filled (see prefill_receipt_from_parse). Run with --apply to write; default is a dry run.
"""

import asyncio
import sys

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.models.ocr_task import OcrTask
from app.models.receipt import Receipt
from app.services.ocr_service import prefill_receipt_from_parse


async def main(apply: bool) -> None:
    async with AsyncSessionLocal() as db:
        receipts = list(await db.scalars(select(Receipt).where(Receipt.ocr_status == "completed")))
        changed = 0
        for receipt in receipts:
            task = await db.scalar(
                select(OcrTask)
                .where(OcrTask.receipt_id == receipt.id, OcrTask.status == "completed")
                .order_by(OcrTask.created_at.desc())
                .limit(1)
            )
            if task is None:
                continue
            before = (receipt.merchant, receipt.category, receipt.amount, receipt.currency, receipt.purchase_date, receipt.warranty_until)
            prefill_receipt_from_parse(receipt, task.parsed_json)
            after = (receipt.merchant, receipt.category, receipt.amount, receipt.currency, receipt.purchase_date, receipt.warranty_until)
            if before != after:
                changed += 1
                print(f"{receipt.id}: {before} -> {after}")
        if apply:
            await db.commit()
        else:
            await db.rollback()
        print(f"{len(receipts)} awaiting review, {changed} {'updated' if apply else 'would change'}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))
