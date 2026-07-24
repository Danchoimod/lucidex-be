import pytest
from beanie import PydanticObjectId, init_beanie
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

from src.admin.models import PlatformAdmin
from src.auth.constants import ActorType
from src.auth.models import Session
from src.auth.services import create_access_token, session_service
from src.config import settings
from src.main import app
from src.organization.constants import AccountStatus, InstitutionRole
from src.organization.models import InstitutionAccount, Organization
from src.owner.constants import OwnerStatus
from src.owner.models import Owner

TEST_DB_NAME = f"{settings.MONGODB_DB_NAME}-test"


@pytest.fixture(autouse=True)
async def init_db():
    client = AsyncIOMotorClient(settings.MONGODB_URI, uuidRepresentation="standard")
    await init_beanie(
        database=client[TEST_DB_NAME],
        document_models=[Session, PlatformAdmin, Owner, InstitutionAccount, Organization],
    )
    await Session.get_motor_collection().delete_many({})
    await PlatformAdmin.get_motor_collection().delete_many({})
    await Owner.get_motor_collection().delete_many({})
    await InstitutionAccount.get_motor_collection().delete_many({})
    await Organization.get_motor_collection().delete_many({})
    yield
    await Session.get_motor_collection().delete_many({})
    await PlatformAdmin.get_motor_collection().delete_many({})
    await Owner.get_motor_collection().delete_many({})
    await InstitutionAccount.get_motor_collection().delete_many({})
    await Organization.get_motor_collection().delete_many({})
    client.close()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_me_platform_admin(client: AsyncClient):
    # 1. Create PlatformAdmin in DB
    admin = PlatformAdmin(
        username="superadmin_test",
        password_hash="hashed_pw",
        role="super_admin",
        twofa_enabled=True,
        status="active",
    )
    await admin.insert()

    # 2. Create session
    session, _ = await session_service.create_session(
        actor_id=str(admin.id),
        actor_type=ActorType.PLATFORM_ADMIN,
    )
    session.twofa_verified = True
    await session.save()

    # 3. Create access token
    access_token = create_access_token(
        subject=str(admin.id),
        actor_type=ActorType.PLATFORM_ADMIN,
        session_id=str(session.id),
    )

    # 4. Call GET /api/v1/auth/me
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["actor_type"] == "platform_admin"
    assert data["actor_id"] == str(admin.id)
    assert data["username"] == "superadmin_test"
    assert data["role"] == "super_admin"
    assert data["status"] == "active"
    assert data["twofa_enabled"] is True


@pytest.mark.asyncio
async def test_get_me_owner(client: AsyncClient):
    # 1. Create Owner in DB
    owner = Owner(
        email="owner_me_test@gmail.com",
        full_name="John Owner",
        status=OwnerStatus.ACTIVE,
    )
    await owner.insert()

    # 2. Create session & token
    session, _ = await session_service.create_session(
        actor_id=str(owner.id),
        actor_type=ActorType.OWNER,
    )
    access_token = create_access_token(
        subject=str(owner.id),
        actor_type=ActorType.OWNER,
        session_id=str(session.id),
    )

    # 3. Call GET /api/v1/auth/me
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["actor_type"] == "owner"
    assert data["actor_id"] == str(owner.id)
    assert data["email"] == "owner_me_test@gmail.com"
    assert data["full_name"] == "John Owner"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_me_institution_account(client: AsyncClient):
    # 1. Create Organization & InstitutionAccount in DB
    org = Organization(
        type="issuer",
        name="Test University",
        tax_code="0123456789",
        address="123 Street",
        legal_rep_name="Dean John",
        contact_email="uni@example.com",
        contact_phone="0901234567",
        registrant_name="Dean John",
    )
    await org.insert()

    account = InstitutionAccount(
        org_id=org.id,
        email="uni_admin@example.com",
        password_hash="hashed_pw",
        role=InstitutionRole.ADMIN,
        status=AccountStatus.ACTIVE,
    )
    await account.insert()

    # 2. Create session & token
    session, _ = await session_service.create_session(
        actor_id=str(account.id),
        actor_type=ActorType.INSTITUTION_ACCOUNT,
        org_id=str(org.id),
    )
    access_token = create_access_token(
        subject=str(account.id),
        actor_type=ActorType.INSTITUTION_ACCOUNT,
        session_id=str(session.id),
        org_id=str(org.id),
    )

    # 3. Call GET /api/v1/auth/me
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["actor_type"] == "institution_account"
    assert data["actor_id"] == str(account.id)
    assert data["email"] == "uni_admin@example.com"
    assert data["org_id"] == str(org.id)
    assert data["organization_name"] == "Test University"
    assert data["role"] == "admin"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_me_unauthorized_without_bearer(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    res_data = response.json()
    assert res_data["success"] is False
    assert res_data["error_code"] == "UNAUTHORIZED"
