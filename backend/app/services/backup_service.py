import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.models.backup_task import BackupTask
from app.models.user import User
from app.services.admin_service import backup_directory
from app.services.audit_service import write_audit_log
from app.services.backup_crypto import ENCRYPTED_SUFFIX, encrypt_file

BACKUP_KEEP = 7


def backup_tables() -> list[str]:
    """Every application table in foreign-key order, so a new model can never be left out of backups."""
    import app.models  # noqa: F401  registers all models on Base.metadata
    from app.core.database import Base

    return [table.name for table in Base.metadata.sorted_tables]


async def create_backup(db: AsyncSession, actor: User, *, backup_type: str = "manual") -> BackupTask:
    task = BackupTask(requested_by_user_id=actor.id, backup_type=backup_type, status="processing", started_at=datetime.now(UTC))
    db.add(task)
    await db.flush()
    await write_audit_log(db, action="backup.create", actor_user_id=actor.id, target_type="backup", target_id=str(task.id))
    try:
        archive_path, manifest = await _write_backup_archive(db, task)
        task.status = "completed"
        task.backup_path = str(archive_path)
        task.file_size = archive_path.stat().st_size
        task.manifest_json = manifest
        task.finished_at = datetime.now(UTC)
        await db.flush()
        await _prune_old_backups(db)
    except Exception as exc:
        task.status = "failed"
        task.error_message = str(exc)
        task.finished_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(task)
    return task


async def delete_backup(db: AsyncSession, actor: User, backup_id) -> None:
    task = await db.get(BackupTask, backup_id)
    if task is None:
        raise AppError("backup_not_found", "Backup not found", 404)
    if task.backup_path:
        path = Path(task.backup_path)
        backup_root = backup_directory().resolve()
        try:
            resolved_path = path.resolve()
        except OSError:
            resolved_path = path
        if resolved_path.is_file() and backup_root in resolved_path.parents:
            resolved_path.unlink()
    await write_audit_log(db, action="backup.delete", actor_user_id=actor.id, target_type="backup", target_id=str(task.id))
    await db.delete(task)
    await db.commit()


async def _write_backup_archive(db: AsyncSession, task: BackupTask) -> tuple[Path, dict]:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    archive_path = backup_directory() / f"xuanbox-backup-{timestamp}-{task.id}.tar.gz{ENCRYPTED_SUFFIX}"
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        plain_archive = tmp_path / "backup.tar.gz"
        database_export = {}
        for table in backup_tables():
            result = await db.execute(text(f"SELECT * FROM {table}"))
            database_export[table] = [dict(row._mapping) for row in result]
        _write_json(tmp_path / "database_export.json", database_export)
        manifest = {
            "backup_id": str(task.id),
            "created_at": timestamp,
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "contents": ["database_export.json", "encrypted_files/", "encrypted_thumbnails/", "encrypted_previews/", "config/"],
            "tables": list(database_export.keys()),
            "encryption": "AES-256-GCM chunks, key = HKDF(MASTER_KEY); restore with python -m app.scripts.restore_backup",
            "not_included": ["encrypted_drop/ (XuanDrop transfers are temporary)"],
            "restore": [
                "Install Docker and clone the repository.",
                "Restore .env values, especially MASTER_KEY and database credentials.",
                "Restore encrypted storage directories into STORAGE_ROOT.",
                "Recreate PostgreSQL data from database_export.json or a future pg_restore dump.",
                "Run docker compose up -d --build.",
            ],
        }
        _write_json(tmp_path / "manifest.json", manifest)
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        _write_json(
            config_dir / "env.example.safe.json",
            {
                "POSTGRES_DB": settings.POSTGRES_DB,
                "POSTGRES_USER": settings.POSTGRES_USER,
                "POSTGRES_HOST": settings.POSTGRES_HOST,
                "POSTGRES_PORT": settings.POSTGRES_PORT,
                "MASTER_KEY": "REDACTED",
                "JWT_SECRET_KEY": "REDACTED",
                "STORAGE_ROOT": settings.STORAGE_ROOT,
            },
        )
        with tarfile.open(plain_archive, "w:gz") as archive:
            archive.add(tmp_path / "manifest.json", arcname="manifest.json")
            archive.add(tmp_path / "database_export.json", arcname="database_export.json")
            archive.add(config_dir, arcname="config")
            storage_root = Path(settings.STORAGE_ROOT)
            for dirname in ("encrypted_files", "encrypted_thumbnails", "encrypted_previews"):
                path = storage_root / dirname
                if path.exists():
                    archive.add(path, arcname=dirname)
        # The database export holds password hashes, OCR text and wrapped file keys: never store it in clear.
        encrypt_file(plain_archive, archive_path)
        return archive_path, manifest


async def _prune_old_backups(db: AsyncSession) -> None:
    """Keep the newest BACKUP_KEEP completed backups; each one is a full copy of the storage."""
    completed = list(
        await db.scalars(select(BackupTask).where(BackupTask.status == "completed").order_by(BackupTask.created_at.desc()))
    )
    for task in completed[BACKUP_KEEP:]:
        if task.backup_path:
            path = Path(task.backup_path)
            if path.is_file() and backup_directory().resolve() in path.resolve().parents:
                path.unlink()
        task.status = "pruned"
        task.backup_path = None


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
