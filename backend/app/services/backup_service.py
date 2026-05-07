import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.backup_task import BackupTask
from app.models.user import User
from app.services.admin_service import backup_directory
from app.services.audit_service import write_audit_log

BACKUP_TABLES = [
    "users",
    "invites",
    "devices",
    "auth_sessions",
    "audit_logs",
    "folders",
    "file_assets",
    "photo_assets",
    "albums",
    "album_photos",
    "tags",
    "tag_links",
    "receipts",
    "documents",
    "shares",
    "share_access_logs",
    "transfer_sessions",
    "transfer_items",
    "ocr_tasks",
    "worker_tasks",
    "backup_tasks",
]


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
    except Exception as exc:
        task.status = "failed"
        task.error_message = str(exc)
        task.finished_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(task)
    return task


async def _write_backup_archive(db: AsyncSession, task: BackupTask) -> tuple[Path, dict]:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    archive_path = backup_directory() / f"xuanbox-backup-{timestamp}-{task.id}.tar.gz"
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        database_export = {}
        for table in BACKUP_TABLES:
            result = await db.execute(text(f"SELECT * FROM {table}"))
            database_export[table] = [dict(row._mapping) for row in result]
        _write_json(tmp_path / "database_export.json", database_export)
        manifest = {
            "backup_id": str(task.id),
            "created_at": timestamp,
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "contents": ["database_export.json", "encrypted_files/", "encrypted_thumbnails/", "encrypted_previews/", "config/"],
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
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(tmp_path / "manifest.json", arcname="manifest.json")
            archive.add(tmp_path / "database_export.json", arcname="database_export.json")
            archive.add(config_dir, arcname="config")
            storage_root = Path(settings.STORAGE_ROOT)
            for dirname in ("encrypted_files", "encrypted_thumbnails", "encrypted_previews"):
                path = storage_root / dirname
                if path.exists():
                    archive.add(path, arcname=dirname)
        return archive_path, manifest


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
