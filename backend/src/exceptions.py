import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.schemas.common import ApiResponse, ValidationErrorData, ValidationIssue

logger = logging.getLogger("lucidex.exception")


class AppError(Exception):
    """Expected application error safe to return to an API client."""

    def __init__(self, status_code: int, message: str, error_code: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.error_code = error_code


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _format_validation_issues(
    exc: RequestValidationError,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    location_prefixes = {"body", "query", "path", "header", "cookie"}

    for error in exc.errors():
        location = [
            str(part)
            for part in error.get("loc", ())
            if part not in location_prefixes
        ]
        message = str(error.get("msg", "Invalid value."))
        if message.startswith("Value error, "):
            message = message.removeprefix("Value error, ")

        issues.append(
            ValidationIssue(
                field=".".join(location) or "request",
                message=message,
                error_type=str(error.get("type", "validation_error")),
            )
        )

    return issues


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def application_error_handler(
        request: Request, exc: AppError
    ) -> JSONResponse:
        logger.warning(
            "application_error",
            extra={
                "request_id": _request_id(request),
                "method": request.method,
                "path": request.url.path,
                "status_code": exc.status_code,
                "actor_type": getattr(request.state, "actor_type", None),
                "error_code": exc.error_code,
            },
        )
        payload = ApiResponse[Any](
            success=False,
            message=exc.message,
            error_code=exc.error_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=payload.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning(
            "request_validation_failed",
            extra={
                "request_id": _request_id(request),
                "method": request.method,
                "path": request.url.path,
                "status_code": 422,
                "actor_type": getattr(request.state, "actor_type", None),
            },
        )
        payload = ApiResponse[ValidationErrorData](
            success=False,
            data=ValidationErrorData(
                errors=_format_validation_issues(exc),
            ),
            message="Request validation failed.",
            error_code="VALIDATION_ERROR",
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.exception_handler(HTTPException)
    async def http_error_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        payload = ApiResponse[Any](
            success=False,
            message=str(exc.detail),
            error_code=f"HTTP_{exc.status_code}",
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=payload.model_dump(),
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            exc_info=exc,
            extra={
                "request_id": _request_id(request),
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "actor_type": getattr(request.state, "actor_type", None),
            },
        )
        payload = ApiResponse[Any](
            success=False,
            message="An unexpected error occurred.",
            error_code="INTERNAL_SERVER_ERROR",
        )
        return JSONResponse(status_code=500, content=payload.model_dump())
