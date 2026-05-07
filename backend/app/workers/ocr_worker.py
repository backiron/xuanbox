import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.services.ocr_service import OCR_TASK_TYPE, process_receipt_ocr_task
from app.services.worker_service import claim_next_worker_task, mark_task_failed

logger = logging.getLogger("xuanbox.worker")


async def process_once() -> bool:
    async with AsyncSessionLocal() as session:
        task = await claim_next_worker_task(session)
        if task is None:
            await session.commit()
            return False
        try:
            if task.task_type == OCR_TASK_TYPE:
                await process_receipt_ocr_task(session, task)
            else:
                await mark_task_failed(session, task, f"Unknown task type: {task.task_type}")
            await session.commit()
        except Exception as exc:
            await mark_task_failed(session, task, str(exc))
            await session.commit()
            logger.exception("Worker task failed: %s", task.id)
        return True


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("XuanBox worker started")
    while True:
        processed = await process_once()
        await asyncio.sleep(0.25 if processed else 2.0)


if __name__ == "__main__":
    asyncio.run(main())
