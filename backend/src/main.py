from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.admin.rate_limit import admin_login_rate_limiter
from src.api.v1 import api_v1_router
from src.config import settings
from src.database import connect_database, disconnect_database
from src.exceptions import register_exception_handlers
from src.logging import configure_logging
from src.middleware import RequestLoggingMiddleware
from src.schemas import ApiResponse, HealthData

configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await connect_database()
    try:
        yield
    finally:
        await admin_login_rate_limiter.close()
        await disconnect_database() 


app = FastAPI(
    title=settings.APP_NAME,
    description="added datetime to admin request",
    version="1.0.38",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

if settings.CORS_ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

register_exception_handlers(app)
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Define HTTP Bearer security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    # Enable BearerAuth globally on Swagger UI
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


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
