import hashlib
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError

import src.invitation.service as invitation_service
from src.exceptions import AppError
from src.invitation.constants import InviteStatus
from src.invitation.service import (
    INVITE_TTL_HOURS,
    rotate_pending_invite,
    validate_pending_invite,
)

ORG_ID = PydanticObjectId("507f1f77bcf86cd799439011")
ADMIN_ID = PydanticObjectId("507f1f77bcf86cd799439012")
INVITE_ID = PydanticObjectId("507f1f77bcf86cd799439013")


@pytest.fixture(autouse=True)
async def invitation_test_database():
    """Override the root MongoDB fixture; these are unit tests."""
    yield


@pytest.fixture(scope="session", autouse=True)
def _drop_test_database_at_session_end():
    yield


@pytest.mark.asyncio
async def test_rotate_revokes_pending_and_stores_only_token_hash(monkeypatch):
    revoked = []
    inserted = []

    async def revoke_pending_for_organization(**kwargs):
        revoked.append(kwargs)
        return 1

    async def insert_invite(invite):
        invite.id = INVITE_ID
        inserted.append(invite)
        return invite

    monkeypatch.setattr(
        invitation_service,
        "revoke_pending_for_organization",
        revoke_pending_for_organization,
    )
    monkeypatch.setattr(invitation_service, "insert_invite", insert_invite)
    monkeypatch.setattr(
        invitation_service.InviteLink,
        "get_motor_collection",
        classmethod(lambda cls: None),
    )

    issued = await rotate_pending_invite(
        organization_id=ORG_ID,
        contact_email="admin@example.com",
        created_by=ADMIN_ID,
    )

    invite = inserted[0]
    assert revoked[0]["organization_id"] == ORG_ID
    assert invite.status == InviteStatus.PENDING
    assert invite.token_hash == hashlib.sha256(
        issued.raw_token.encode("utf-8")
    ).hexdigest()
    assert issued.raw_token != invite.token_hash
    assert issued.invite_id == INVITE_ID
    assert timedelta(hours=INVITE_TTL_HOURS - 1) < (
        issued.expires_at - invite.created_at
    ) <= timedelta(hours=INVITE_TTL_HOURS)


@pytest.mark.asyncio
async def test_rotate_maps_duplicate_key_to_safe_conflict(monkeypatch):
    async def revoke_pending_for_organization(**_):
        return 1

    async def insert_invite(_):
        raise DuplicateKeyError("duplicate token_hash and index details")

    monkeypatch.setattr(
        invitation_service,
        "revoke_pending_for_organization",
        revoke_pending_for_organization,
    )
    monkeypatch.setattr(invitation_service, "insert_invite", insert_invite)
    monkeypatch.setattr(
        invitation_service.InviteLink,
        "get_motor_collection",
        classmethod(lambda cls: None),
    )

    with pytest.raises(AppError) as exc_info:
        await rotate_pending_invite(
            organization_id=ORG_ID,
            contact_email="admin@example.com",
            created_by=ADMIN_ID,
        )

    error = exc_info.value
    assert error.status_code == 409
    assert error.error_code == "INVITATION_ROTATION_CONFLICT"
    assert "token_hash" not in error.message
    assert "index" not in error.message


@pytest.mark.asyncio
async def test_validate_pending_invite_returns_shared_context(monkeypatch):
    raw_token = "valid-raw-token"
    mongo_session = object()
    calls = []
    invite = SimpleNamespace(
        id=INVITE_ID,
        org_id=ORG_ID,
        contact_email="admin@example.com",
        status=InviteStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )

    async def find_by_token_hash(**kwargs):
        calls.append(kwargs)
        return invite

    monkeypatch.setattr(
        invitation_service,
        "find_by_token_hash",
        find_by_token_hash,
    )

    context = await validate_pending_invite(
        raw_token=raw_token,
        session=mongo_session,
    )

    assert calls == [
        {
            "token_hash": hashlib.sha256(raw_token.encode()).hexdigest(),
            "session": mongo_session,
        }
    ]
    assert context.invite_id == INVITE_ID
    assert context.org_id == ORG_ID
    assert context.contact_email == "admin@example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["missing", "expired"])
async def test_validate_pending_invite_rejects_invalid_or_expired_token(
    monkeypatch,
    case,
):
    invite = None
    if case == "expired":
        invite = SimpleNamespace(
            id=INVITE_ID,
            org_id=ORG_ID,
            contact_email="admin@example.com",
            status=InviteStatus.PENDING,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )

    async def find_by_token_hash(**_):
        return invite

    monkeypatch.setattr(
        invitation_service,
        "find_by_token_hash",
        find_by_token_hash,
    )

    with pytest.raises(AppError) as exc_info:
        await validate_pending_invite(raw_token="invalid-token")

    assert exc_info.value.error_code == "INVALID_INVITE"
