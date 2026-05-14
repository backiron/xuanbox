import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.backup_task import BackupTask
from app.models.user import User
from app.services.backup_service import create_backup
from app.services.document_intelligence_service import DOCUMENT_EXTRACT_TASK_TYPE, process_document_extract_task
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
            elif task.task_type == DOCUMENT_EXTRACT_TASK_TYPE:
                await process_document_extract_task(session, task)
            else:
                await mark_task_failed(session, task, f"Unknown task type: {task.task_type}")
            await session.commit()
        except Exception as exc:
            await mark_task_failed(session, task, str(exc))
            await session.commit()
            logger.exception("Worker task failed: %s", task.id)
        return True


async def run_scheduled_backup_if_due() -> None:
    if settings.BACKUP_SCHEDULE_HOURS <= 0:
        return
    async with AsyncSessionLocal() as session:
        cutoff = datetime.now(UTC) - timedelta(hours=settings.BACKUP_SCHEDULE_HOURS)
        recent = await session.scalar(
            select(BackupTask)
            .where(BackupTask.backup_type == "scheduled", BackupTask.status == "completed", BackupTask.finished_at >= cutoff)
            .order_by(BackupTask.finished_at.desc())
            .limit(1)
        )
        if recent is not None:
            return
        actor = await session.scalar(
            select(User)
            .where(User.status == "active", User.role.in_(("owner", "admin")))
            .order_by(User.created_at.asc())
            .limit(1)
        )
        if actor is None:
            return
        backup = await create_backup(session, actor, backup_type="scheduled")
        logger.info("Scheduled backup %s finished with status %s", backup.id, backup.status)


async def scheduled_backup_loop() -> None:
    while True:
        try:
            await run_scheduled_backup_if_due()
        except Exception:
            logger.exception("Scheduled backup check failed")
        await asyncio.sleep(3600)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("XuanBox worker started")
    asyncio.create_task(scheduled_backup_loop())
    while True:
        processed = await process_once()
        await asyncio.sleep(0.25 if processed else 2.0)


if __name__ == "__main__":
    asyncio.run(main())
