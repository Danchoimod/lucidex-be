import pytest
from httpx import ASGITransport, AsyncClient
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from src.main import app
from src.config import settings
from src.owner.models import Owner
from src.organization.models import InstitutionAccount, Organization
from src.invitation.models import InviteLink
from src.auth.models import Session
from src.otp.models import OtpCode


@pytest.fixture(autouse=True)
async def init_test_db():
    test_db_name = f"{settings.MONGODB_DB_NAME}-test"
    client = AsyncIOMotorClient(settings.MONGODB_URI, uuidRepresentation="standard")
    await init_beanie(
        database=client[test_db_name],
        document_models=[Owner, InstitutionAccount, Organization, InviteLink, Session, OtpCode]
    )
    yield
    client.close()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_debug_delete_user(client: AsyncClient):
    email = "debug_tester_123@example.com"

    # Create dummy owner
    owner = Owner(email=email, status="active")
    await owner.insert()

    # Call POST /api/v1/debug/delete-user
    response = await client.post(
        "/api/v1/debug/delete-user",
        json={"email": email}
    )

    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert res["data"]["deleted_owners"] == 1

    # Verify user is deleted
    assert await Owner.find_one(Owner.email == email) is None
