import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.common import ApiResponse

logger = logging.getLogger("lucidex.exception")


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, _: RequestValidationError
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
        payload = ApiResponse[Any](
            success=False,
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
