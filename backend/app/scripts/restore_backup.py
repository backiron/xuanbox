import argparse
import json
import shutil
import tarfile
from pathlib import Path

from sqlalchemy import create_engine, text

from app.core.config import settings
from app.services.backup_service import BACKUP_TABLES


def normalize_row(row: dict) -> dict:
    normalized = {}
    for key, value in row.items():
        if isinstance(value, (dict, list)):
            normalized[key] = json.dumps(value, ensure_ascii=False)
        else:
            normalized[key] = value
    return normalized


def safe_extract(archive: tarfile.TarFile, target: Path) -> None:
    target_root = target.resolve()
    for member in archive.getmembers():
        member_path = (target / member.name).resolve()
        if target_root not in (member_path, *member_path.parents):
            raise SystemExit(f"Unsafe backup archive member: {member.name}")
    archive.extractall(target)


def restore_archive(archive_path: Path, *, storage_root: Path, yes: bool) -> None:
    if not yes:
        raise SystemExit("Refusing to restore without --yes")
    if not archive_path.exists():
        raise SystemExit(f"Backup archive not found: {archive_path}")

    extract_root = storage_root / "restore_tmp" / archive_path.stem
    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path, "r:gz") as archive:
        safe_extract(archive, extract_root)

    database_export_path = extract_root / "database_export.json"
    if not database_export_path.exists():
        raise SystemExit("Backup archive is missing database_export.json")

    for dirname in ("encrypted_files", "encrypted_thumbnails", "encrypted_previews"):
        source = extract_root / dirname
        if source.exists():
            target = storage_root / dirname
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)

    database_export = json.loads(database_export_path.read_text(encoding="utf-8"))
    engine = create_engine(settings.sync_database_url)
    with engine.begin() as connection:
        for table in reversed(BACKUP_TABLES):
            connection.execute(text(f'DELETE FROM "{table}"'))
        for table in BACKUP_TABLES:
            rows = [normalize_row(row) for row in database_export.get(table, [])]
            if not rows:
                continue
            columns = list(rows[0].keys())
            column_sql = ", ".join(f'"{column}"' for column in columns)
            value_sql = ", ".join(f":{column}" for column in columns)
            statement = text(f'INSERT INTO "{table}" ({column_sql}) VALUES ({value_sql})')
            connection.execute(statement, rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore a XuanBox backup archive into the configured database and storage root.")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--storage-root", type=Path, default=Path(settings.STORAGE_ROOT))
    parser.add_argument("--yes", action="store_true", help="Confirm that the target database and storage can be overwritten.")
    args = parser.parse_args()
    restore_archive(args.archive, storage_root=args.storage_root, yes=args.yes)


if __name__ == "__main__":
    main()
