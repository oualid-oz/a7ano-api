from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.common.responses import error_response


class AppException(Exception):
    status_code: int = HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.errors = errors or []
        super().__init__(self.message)


class ValidationException(AppException):
    status_code = HTTP_422_UNPROCESSABLE_CONTENT
    code = "VALIDATION_ERROR"
    message = "Validation failed."


class BadRequestException(AppException):
    status_code = HTTP_400_BAD_REQUEST
    code = "BAD_REQUEST"
    message = "Bad request."


class AuthenticationException(AppException):
    status_code = HTTP_401_UNAUTHORIZED
    code = "AUTHENTICATION_ERROR"
    message = "Authentication required."


class AuthorizationException(AppException):
    status_code = HTTP_403_FORBIDDEN
    code = "PERMISSION_DENIED"
    message = "Permission denied."


class ResourceNotFoundException(AppException):
    status_code = HTTP_404_NOT_FOUND
    code = "RESOURCE_NOT_FOUND"
    message = "Resource not found."


class DuplicateValueException(AppException):
    status_code = HTTP_409_CONFLICT
    code = "DUPLICATE_VALUE"
    message = "A resource with this value already exists."


class RateLimitException(AppException):
    status_code = HTTP_429_TOO_MANY_REQUESTS
    code = "RATE_LIMIT_EXCEEDED"
    message = "Rate limit exceeded. Please try again later."


class ConflictException(AppException):
    status_code = HTTP_409_CONFLICT
    code = "CONFLICT"
    message = "Conflict with the current state."


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=exc.message,
            code=exc.code,
            errors=exc.errors,
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            message="An unexpected error occurred.",
            code="INTERNAL_ERROR",
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)
