import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from beanie import PydanticObjectId
from fastapi import FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials

import src.admin.dependencies as admin_dependencies
import src.admin.services.organizations as organization_service
from src.admin.dependencies import require_admin, require_super_admin
from src.admin.routers.organizations import router as organizations_router
from src.admin.services.organizations import approve_organization
from src.auth.constants import ActorType, SessionStatus
from src.exceptions import AppError
from src.invitation.constants import InviteStatus
from src.invitation.schemas import IssuedInvite
from src.mailer import EmailDeliveryError
from src.organization.constants import OrganizationStatus

ADMIN_ID = PydanticObjectId("507f1f77bcf86cd799439012")
ORG_ID = PydanticObjectId("507f1f77bcf86cd799439011")
INVITE_ID = PydanticObjectId("507f1f77bcf86cd799439013")
SESSION_ID = PydanticObjectId("507f1f77bcf86cd799439014")


@pytest.fixture(autouse=True)
async def admin_organization_test_database():
    """Override the root MongoDB fixture; these are unit tests."""
    yield


@pytest.fixture(scope="session", autouse=True)
def _drop_test_database_at_session_end():
    yield


def fake_admin(role="super_admin"):
    return SimpleNamespace(id=ADMIN_ID, role=role, status="active")


def fake_organization():
    return SimpleNamespace(
        id=ORG_ID,
        status=OrganizationStatus.APPROVED,
        name="Lucidex Institution",
        contact_email="institution@example.com",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["super_admin", "operations_admin"])
async def test_require_admin_accepts_supported_admin_roles(monkeypatch, role):
    admin = fake_admin(role=role)
    session = SimpleNamespace(
        id=SESSION_ID,
        actor_id=ADMIN_ID,
        actor_type=ActorType.PLATFORM_ADMIN,
        status=SessionStatus.ACTIVE,
        twofa_verified=True,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    monkeypatch.setattr(
        admin_dependencies,
        "decode_access_token",
        lambda _: {
            "sub": str(ADMIN_ID),
            "actor_type": ActorType.PLATFORM_ADMIN,
            "session_id": str(SESSION_ID),
            "exp": datetime.now(UTC) + timedelta(minutes=10),
        },
    )

    async def get_session(_):
        return session

    async def get_admin(_):
        return admin

    monkeypatch.setattr(admin_dependencies.Session, "get", get_session)
    monkeypatch.setattr(admin_dependencies.PlatformAdmin, "get", get_admin)
    request = Request({"type": "http"})

    result = await require_admin(
        request,
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="token"),
    )

    assert result is admin
    assert request.state.actor_type == ActorType.PLATFORM_ADMIN


@pytest.mark.asyncio
async def test_non_super_admin_is_rejected():
    with pytest.raises(AppError) as exc_info:
        await require_super_admin(fake_admin(role="operations_admin"))

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == "SUPER_ADMIN_REQUIRED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "frontend_base_url",
    ["https://frontend.example", "https://frontend.example/"],
)
async def test_admin_roles_approve_and_reinvite_without_leaking_token(
    monkeypatch,
    caplog,
    frontend_base_url,
):
    caplog.set_level(logging.INFO, logger="lucidex.admin.organizations")
    monkeypatch.setattr(
        organization_service.settings,
        "FRONTEND_BASE_URL",
        frontend_base_url,
    )
    rotate_calls = []
    sent = []

    async def approve_if_needed(**_):
        return fake_organization()

    async def rotate_pending_invite(**kwargs):
        rotate_calls.append(kwargs)
        return IssuedInvite(
            invite_id=INVITE_ID,
            raw_token=f"raw-secret-invite-token-{len(rotate_calls)}",
            expires_at=datetime.now(UTC) + timedelta(hours=72),
        )

    async def send_email(**kwargs):
        sent.append(kwargs)

    async def find_pending_by_id(**_):
        return SimpleNamespace(status=InviteStatus.PENDING)

    monkeypatch.setattr(
        organization_service,
        "_approve_if_needed",
        approve_if_needed,
    )
    monkeypatch.setattr(
        organization_service,
        "rotate_pending_invite",
        rotate_pending_invite,
    )
    monkeypatch.setattr(
        organization_service.mailer_service,
        "send_email",
        send_email,
    )
    monkeypatch.setattr(
        organization_service,
        "find_pending_by_id",
        find_pending_by_id,
    )

    result = await approve_organization(
        organization_id=ORG_ID,
        admin=fake_admin(role="super_admin"),
        request_id="approve-super-request",
    )
    second_result = await approve_organization(
        organization_id=ORG_ID,
        admin=fake_admin(role="operations_admin"),
        request_id="approve-operations-request",
    )

    assert len(rotate_calls) == 2
    assert sent[0]["email"] == "institution@example.com"
    assert sent[1]["email"] == "institution@example.com"
    assert sent[0]["context"]["invite_url"] == (
        "https://frontend.example/invite?token=raw-secret-invite-token-1"
    )
    assert sent[1]["context"]["invite_url"] == (
        "https://frontend.example/invite?token=raw-secret-invite-token-2"
    )
    assert sent[0]["context"]["contact_email"] == "institution@example.com"
    assert "//invite" not in sent[0]["context"]["invite_url"]
    assert sent[0]["context"]["expires_in_hours"] == 72
    assert result.organization_status == OrganizationStatus.APPROVED
    assert result.invite_status == InviteStatus.PENDING
    assert result.email_sent is True
    assert "raw-secret-invite-token" not in result.model_dump_json()
    assert "raw-secret-invite-token" not in second_result.model_dump_json()
    assert "token_hash" not in result.model_dump_json()
    assert "invite_url" not in result.model_dump_json()
    assert "invite_url" not in second_result.model_dump_json()
    records = [
        record
        for record in caplog.records
        if record.getMessage() == "organization_approved_and_invited"
    ]
    assert [record.request_id for record in records] == [
        "approve-super-request",
        "approve-operations-request",
    ]
    assert [record.actor_role for record in records] == [
        "super_admin",
        "operations_admin",
    ]
    assert all(record.organization_id == str(ORG_ID) for record in records)
    assert "raw-secret-invite-token" not in caplog.text
    assert "institution@example.com" not in caplog.text


def test_approve_openapi_example_has_approved_status():
    app = FastAPI()
    app.include_router(organizations_router, prefix="/api/v1")

    response = app.openapi()["paths"][
        "/api/v1/admin/organizations/{organization_id}/approve"
    ]["post"]["responses"]["200"]
    example = response["content"]["application/json"]["example"]

    assert example["data"]["organization_status"] == "approved"
    assert example["message"] == "Organization approved and invitation sent."
    assert "error_code" not in example


@pytest.mark.asyncio
async def test_email_failure_revokes_new_invite(monkeypatch, caplog):
    revoked = []

    async def approve_if_needed(**_):
        return fake_organization()

    async def rotate_pending_invite(**_):
        return IssuedInvite(
            invite_id=INVITE_ID,
            raw_token="raw-token",
            expires_at=datetime.now(UTC) + timedelta(hours=72),
        )

    async def send_email(**_):
        raise EmailDeliveryError()

    async def find_pending_by_id(**_):
        return SimpleNamespace(status=InviteStatus.PENDING)

    async def revoke_if_pending(**kwargs):
        revoked.append(kwargs)
        return True

    monkeypatch.setattr(
        organization_service,
        "_approve_if_needed",
        approve_if_needed,
    )
    monkeypatch.setattr(
        organization_service,
        "rotate_pending_invite",
        rotate_pending_invite,
    )
    monkeypatch.setattr(
        organization_service.mailer_service,
        "send_email",
        send_email,
    )
    monkeypatch.setattr(
        organization_service,
        "find_pending_by_id",
        find_pending_by_id,
    )
    monkeypatch.setattr(
        organization_service,
        "revoke_if_pending",
        revoke_if_pending,
    )

    with pytest.raises(AppError) as exc_info:
        await approve_organization(
            organization_id=ORG_ID,
            admin=fake_admin(),
        )

    assert exc_info.value.error_code == "INVITATION_EMAIL_FAILED"
    assert revoked[0]["invite_id"] == INVITE_ID
    assert exc_info.value.log_context == {
        "actor_id": str(ADMIN_ID),
        "actor_role": "super_admin",
        "organization_id": str(ORG_ID),
        "invite_id": str(INVITE_ID),
        "failure_reason": "EmailDeliveryError",
    }
    assert "raw-token" not in str(exc_info.value.log_context)
    assert "institution@example.com" not in str(exc_info.value.log_context)
    assert not caplog.records


@pytest.mark.asyncio
async def test_no_longer_pending_invite_is_not_emailed(monkeypatch):
    sent = []

    async def approve_if_needed(**_):
        return fake_organization()

    async def rotate_pending_invite(**_):
        return IssuedInvite(
            invite_id=INVITE_ID,
            raw_token="raw-token",
            expires_at=datetime.now(UTC) + timedelta(hours=72),
        )

    async def find_pending_by_id(**_):
        return None

    async def send_email(**kwargs):
        sent.append(kwargs)

    monkeypatch.setattr(
        organization_service,
        "_approve_if_needed",
        approve_if_needed,
    )
    monkeypatch.setattr(
        organization_service,
        "rotate_pending_invite",
        rotate_pending_invite,
    )
    monkeypatch.setattr(
        organization_service,
        "find_pending_by_id",
        find_pending_by_id,
    )
    monkeypatch.setattr(
        organization_service.mailer_service,
        "send_email",
        send_email,
    )

    with pytest.raises(AppError) as exc_info:
        await approve_organization(
            organization_id=ORG_ID,
            admin=fake_admin(),
        )

    assert exc_info.value.error_code == "INVITATION_ROTATION_CONFLICT"
    assert sent == []
