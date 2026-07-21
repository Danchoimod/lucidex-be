from datetime import UTC, datetime, timedelta

import pytest
from beanie import PydanticObjectId, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

from src.auth.services import verify_password
from src.config import settings
from src.invitation.constants import InviteStatus
from src.invitation.models import InviteLink
from src.invitation.service import hash_invite_token, validate_pending_invite
from src.organization.constants import AccountStatus
from src.organization.models import InstitutionAccount
from src.organization.services.invitation import submit_invite_password


@pytest.fixture(autouse=True)
async def otp_test_database():
    """Override the root OTP database fixture for this integration test."""
    yield


@pytest.fixture(scope="session", autouse=True)
def _drop_test_database_at_session_end():
    """The test owns and cleans only its InviteLink collection."""
    yield


@pytest.mark.asyncio
async def test_invite_round_trip_preserves_utc_and_validates():
    database_name = f"{settings.MONGODB_DB_NAME}-test"
    client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        uuidRepresentation="standard",
        serverSelectionTimeoutMS=3000,
    )

    try:
        await client.admin.command("ping")
        await init_beanie(
            database=client[database_name],
            document_models=[InviteLink, InstitutionAccount],
        )
    except (PyMongoError, OSError) as exc:
        client.close()
        pytest.skip(f"Integration MongoDB is unavailable: {type(exc).__name__}")

    collection = InviteLink.get_motor_collection()
    account_collection = InstitutionAccount.get_motor_collection()
    await collection.delete_many({})
    await account_collection.delete_many({})
    raw_token = "integration-invite-token"
    now = datetime.now(UTC)
    invite = InviteLink(
        org_id=PydanticObjectId("507f1f77bcf86cd799439011"),
        contact_email="admin@example.com",
        token_hash=hash_invite_token(raw_token),
        status=InviteStatus.PENDING,
        expires_at=now + timedelta(hours=72),
        created_by=PydanticObjectId("507f1f77bcf86cd799439012"),
        created_at=now,
        updated_at=now,
    )

    try:
        await invite.insert()
        stored = await InviteLink.get(invite.id)

        assert stored is not None
        assert stored.expires_at.tzinfo is not None
        assert stored.created_at.tzinfo is not None
        assert stored.updated_at.tzinfo is not None
        assert stored.expires_at.utcoffset() == timedelta(0)
        assert stored.created_at.utcoffset() == timedelta(0)
        assert stored.updated_at.utcoffset() == timedelta(0)

        context = await validate_pending_invite(raw_token=raw_token)
        assert context.invite_id == invite.id
        assert context.org_id == invite.org_id

        account = await submit_invite_password(
            invite_token=raw_token,
            password="initial-password",
        )
        assert account.status == AccountStatus.PENDING
        assert account.password_hash != "initial-password"
        assert verify_password("initial-password", account.password_hash)

        updated = await submit_invite_password(
            invite_token=raw_token,
            password="replacement-password",
        )
        assert updated.id == account.id
        assert await InstitutionAccount.find({"org_id": invite.org_id}).count() == 1
        assert verify_password("replacement-password", updated.password_hash)

        stored_invite = await InviteLink.get(invite.id)
        assert stored_invite is not None
        assert stored_invite.status == InviteStatus.PENDING
    finally:
        await collection.delete_many({})
        await account_collection.delete_many({})
        client.close()
