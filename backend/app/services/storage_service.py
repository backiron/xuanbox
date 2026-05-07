from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.core.config import settings


def encrypted_file_path(owner_id: UUID, file_id: UUID) -> Path:
    now = datetime.now(UTC)
    return (
        Path(settings.STORAGE_ROOT)
        / "encrypted_files"
        / str(owner_id)
        / f"{now.year:04d}"
        / f"{now.month:02d}"
        / f"{file_id}.bin"
    )


def encrypted_derivative_path(owner_id: UUID, file_id: UUID, derivative_type: str) -> Path:
    now = datetime.now(UTC)
    directory = "encrypted_thumbnails" if derivative_type == "thumbnail" else "encrypted_previews"
    return (
        Path(settings.STORAGE_ROOT)
        / directory
        / str(owner_id)
        / f"{now.year:04d}"
        / f"{now.month:02d}"
        / f"{file_id}.bin"
    )


async def save_encrypted_file(path: Path, encrypted_bytes: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encrypted_bytes)


def read_encrypted_file(path: str) -> bytes:
    return Path(path).read_bytes()


def delete_physical_file(path: str) -> None:
    file_path = Path(path)
    if file_path.exists():
        file_path.unlink()
