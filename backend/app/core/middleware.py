import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger("lucidex.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach a request ID and emit one metadata-only log per HTTP request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.actor_type = None
        started_at = time.perf_counter()

        response = await call_next(request)
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        level = logging.INFO
        if 400 <= response.status_code < 500:
            level = logging.WARNING
        elif response.status_code >= 500:
            level = logging.ERROR

        logger.log(
            level,
            "http_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "actor_type": request.state.actor_type,
            },
        )
        return response
