from typing import Any


def success_response(
    data: Any = None,
    message: str = "OK",
    code: str = "OK",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "code": code,
        "data": data,
        "meta": meta,
    }


def error_response(
    message: str = "An error occurred.",
    code: str = "INTERNAL_ERROR",
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "code": code,
        "errors": errors or [],
    }
