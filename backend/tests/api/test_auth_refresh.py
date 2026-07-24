import pytest
from httpx import ASGITransport, AsyncClient
from beanie import PydanticObjectId, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from src.auth.constants import ActorType
from src.auth.models import Session
from src.auth.services import session_service
from src.config import settings
from src.main import app

TEST_DB_NAME = f"{settings.MONGODB_DB_NAME}-test"


@pytest.fixture(autouse=True)
async def init_db():
    client = AsyncIOMotorClient(settings.MONGODB_URI, uuidRepresentation="standard")
    await init_beanie(database=client[TEST_DB_NAME], document_models=[Session])
    await Session.get_motor_collection().delete_many({})
    yield
    await Session.get_motor_collection().delete_many({})
    client.close()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient):
    # 1. Create active session
    actor_id = str(PydanticObjectId())
    session, raw_refresh_token = await session_service.create_session(
        actor_id=actor_id,
        actor_type=ActorType.OWNER,
    )

    # 2. Call POST /api/v1/auth/refresh
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": raw_refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_refresh_token_string"},
    )

    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "INVALID_REFRESH_TOKEN"
