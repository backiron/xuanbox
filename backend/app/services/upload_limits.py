from fastapi import UploadFile, status

from app.core.errors import AppError

MAX_FILE_UPLOAD_BYTES = 200 * 1024 * 1024
MAX_IMAGE_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_AVATAR_UPLOAD_BYTES = 2 * 1024 * 1024


def format_size(bytes_count: int) -> str:
    if bytes_count % (1024 * 1024) == 0:
        return f"{bytes_count // (1024 * 1024)} MB"
    return f"{bytes_count / 1024 / 1024:.1f} MB"


def max_bytes_for_user_upload(upload: UploadFile) -> int:
    if upload.content_type and upload.content_type.startswith("image/"):
        return MAX_IMAGE_UPLOAD_BYTES
    return MAX_FILE_UPLOAD_BYTES


def _content_length(upload: UploadFile) -> int | None:
    value = upload.headers.get("content-length") if upload.headers else None
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def validate_declared_size(upload: UploadFile, max_bytes: int, error_code: str = "file_too_large") -> None:
    declared = _content_length(upload)
    if declared is not None and declared > max_bytes:
        raise AppError(
            error_code,
            f"Upload is too large. Maximum allowed size is {format_size(max_bytes)}.",
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


async def read_upload_bytes(
    upload: UploadFile,
    *,
    max_bytes: int,
    empty_error_code: str = "empty_file",
    empty_message: str = "Uploaded file is empty",
    too_large_error_code: str = "file_too_large",
) -> bytes:
    validate_declared_size(upload, max_bytes, too_large_error_code)
    content = await upload.read()
    if not content:
        raise AppError(empty_error_code, empty_message, status.HTTP_400_BAD_REQUEST)
    if len(content) > max_bytes:
        raise AppError(
            too_large_error_code,
            f"Upload is too large. Maximum allowed size is {format_size(max_bytes)}.",
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
    return content


async def read_user_upload_bytes(upload: UploadFile) -> bytes:
    return await read_upload_bytes(upload, max_bytes=max_bytes_for_user_upload(upload))
