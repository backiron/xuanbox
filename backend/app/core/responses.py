from typing import Any

from pydantic import BaseModel


class ApiResponse(BaseModel):
    success: bool = True
    data: Any = None
    message: str = "ok"


class ApiErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    message: str


def success_response(data: Any = None, message: str = "ok") -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "message": message,
    }


def error_response(error_code: str, message: str) -> dict[str, Any]:
    return {
        "success": False,
        "error_code": error_code,
        "message": message,
    }
