from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.worker_task import WorkerTask


async def enqueue_worker_task(
    db: AsyncSession,
    *,
    task_type: str,
    owner_id: UUID | None,
    target_type: str | None = None,
    target_id: UUID | None = None,
    payload_json: dict | None = None,
) -> WorkerTask:
    task = WorkerTask(
        owner_id=owner_id,
        task_type=task_type,
        target_type=target_type,
        target_id=target_id,
        status="pending",
        payload_json=payload_json,
        scheduled_at=datetime.now(UTC),
    )
    db.add(task)
    await db.flush()
    return task


async def claim_next_worker_task(db: AsyncSession) -> WorkerTask | None:
    task = await db.scalar(
        select(WorkerTask)
        .where(WorkerTask.status == "pending", WorkerTask.scheduled_at <= datetime.now(UTC))
        .order_by(WorkerTask.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if task is None:
        return None
    task.status = "processing"
    task.started_at = datetime.now(UTC)
    task.attempts += 1
    await db.flush()
    return task


async def mark_task_completed(db: AsyncSession, task: WorkerTask) -> None:
    task.status = "completed"
    task.finished_at = datetime.now(UTC)
    task.error_message = None
    await db.flush()


async def mark_task_failed(db: AsyncSession, task: WorkerTask, error_message: str) -> None:
    task.status = "failed"
    task.finished_at = datetime.now(UTC)
    task.error_message = error_message[:2000]
    await db.flush()
