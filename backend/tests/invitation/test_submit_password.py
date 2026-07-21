from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from beanie import PydanticObjectId

import src.organization.services.invitation as account_service
from src.exceptions import AppError
from src.invitation.schemas import InviteContext
from src.organization.constants import AccountStatus

ORG_ID = PydanticObjectId("507f1f77bcf86cd799439011")
ACCOUNT_ID = PydanticObjectId("507f1f77bcf86cd799439014")
INVITE_ID = PydanticObjectId("507f1f77bcf86cd799439013")


@pytest.fixture(autouse=True)
async def invitation_test_database():
    """Override the root MongoDB fixture; these are unit tests."""
    yield


@pytest.fixture(scope="session", autouse=True)
def _drop_test_database_at_session_end():
    yield


def invite_context() -> InviteContext:
    return InviteContext(
        invite_id=INVITE_ID,
        org_id=ORG_ID,
        contact_email="admin@example.com",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )


@pytest.mark.asyncio
async def test_valid_invite_creates_pending_account_with_hashed_password(
    monkeypatch,
):
    created = []

    async def validate_pending_invite(**_):
        return invite_context()

    async def find_account(**_):
        return None

    async def create_account(account):
        account.id = ACCOUNT_ID
        created.append(account)
        return account

    monkeypatch.setattr(
        account_service,
        "validate_pending_invite",
        validate_pending_invite,
    )
    monkeypatch.setattr(
        account_service,
        "find_institution_account_by_org_id",
        find_account,
    )
    monkeypatch.setattr(
        account_service,
        "create_institution_account",
        create_account,
    )
    monkeypatch.setattr(
        account_service,
        "get_password_hash",
        lambda password: f"hashed:{password}",
    )
    monkeypatch.setattr(
        account_service.InstitutionAccount,
        "get_motor_collection",
        classmethod(lambda cls: None),
    )

    account = await account_service.submit_invite_password(
        invite_token="raw-token",
        password="new-password",
    )

    assert account.status == AccountStatus.PENDING
    assert account.password_hash == "hashed:new-password"
    assert account.password_hash != "new-password"
    assert len(created) == 1


@pytest.mark.asyncio
async def test_resubmit_updates_only_pending_password_without_duplicate(monkeypatch):
    existing = SimpleNamespace(
        id=ACCOUNT_ID,
        org_id=ORG_ID,
        email="admin@example.com",
        password_hash="old-hash",
        status=AccountStatus.PENDING,
    )
    created = []
    updates = []

    async def validate_pending_invite(**_):
        return invite_context()

    async def find_account(**_):
        return existing

    async def create_account(account):
        created.append(account)
        return account

    async def update_password(**kwargs):
        updates.append(kwargs)
        existing.password_hash = kwargs["password_hash"]
        return existing

    monkeypatch.setattr(
        account_service,
        "validate_pending_invite",
        validate_pending_invite,
    )
    monkeypatch.setattr(
        account_service,
        "find_institution_account_by_org_id",
        find_account,
    )
    monkeypatch.setattr(
        account_service,
        "create_institution_account",
        create_account,
    )
    monkeypatch.setattr(
        account_service,
        "update_pending_password",
        update_password,
    )
    monkeypatch.setattr(
        account_service,
        "get_password_hash",
        lambda password: f"hashed:{password}",
    )

    account = await account_service.submit_invite_password(
        invite_token="raw-token",
        password="replacement-password",
    )

    assert account is existing
    assert created == []
    assert updates == [
        {
            "org_id": ORG_ID,
            "password_hash": "hashed:replacement-password",
        }
    ]


@pytest.mark.asyncio
async def test_active_account_rejects_password_submit(monkeypatch):
    active_account = SimpleNamespace(
        id=ACCOUNT_ID,
        org_id=ORG_ID,
        email="admin@example.com",
        password_hash="existing-hash",
        status=AccountStatus.ACTIVE,
    )

    async def validate_pending_invite(**_):
        return invite_context()

    async def find_account(**_):
        return active_account

    monkeypatch.setattr(
        account_service,
        "validate_pending_invite",
        validate_pending_invite,
    )
    monkeypatch.setattr(
        account_service,
        "find_institution_account_by_org_id",
        find_account,
    )
    monkeypatch.setattr(
        account_service,
        "get_password_hash",
        lambda password: f"hashed:{password}",
    )

    with pytest.raises(AppError) as exc_info:
        await account_service.submit_invite_password(
            invite_token="raw-token",
            password="new-password",
        )

    assert exc_info.value.error_code == "INSTITUTION_ACCOUNT_ALREADY_ACTIVE"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["invalid", "expired"])
async def test_invalid_or_expired_invite_returns_invalid_invite(monkeypatch, case):
    async def validate_pending_invite(**_):
        raise AppError(
            status_code=400,
            message="Invalid or expired invitation link.",
            error_code="INVALID_INVITE",
        )

    monkeypatch.setattr(
        account_service,
        "validate_pending_invite",
        validate_pending_invite,
    )

    with pytest.raises(AppError) as exc_info:
        await account_service.submit_invite_password(
            invite_token=f"{case}-token",
            password="new-password",
        )

    assert exc_info.value.error_code == "INVALID_INVITE"
