from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_v1_router
from app.core.config import settings
from app.core.database import connect_database, disconnect_database
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware
from app.schemas import ApiResponse, HealthData

configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await connect_database()
    try:
        yield
    finally:
        await disconnect_database()


app = FastAPI(
    title=settings.APP_NAME,
    description="API-first backend for the Lucidex credential platform.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

if settings.CORS_ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

register_exception_handlers(app)
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get(
    "/health",
    response_model=ApiResponse[HealthData],
    summary="Check API health",
    description="Returns HTTP 200 when the Lucidex API process is available.",
    tags=["Operations"],
)
async def health_check() -> ApiResponse[HealthData]:
    return ApiResponse(
        success=True,
        data=HealthData(status="ok"),
        message="Lucidex API is healthy.",
    )
