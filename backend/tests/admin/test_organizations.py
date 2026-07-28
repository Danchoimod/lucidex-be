import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from beanie import PydanticObjectId
from fastapi import FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

import src.admin.dependencies as admin_dependencies
import src.admin.services.organizations as organization_service
from src.admin.dependencies import require_admin, require_super_admin
from src.admin.routers.organizations import router as organizations_router
from src.admin.services.organizations import approve_organization, reject_organization
from src.auth.constants import ActorType, SessionStatus
from src.exceptions import AppError, register_exception_handlers
from src.invitation.constants import InviteStatus
from src.invitation.schemas import IssuedInvite
from src.mailer import EmailDeliveryError, EmailTemplate
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


def fake_organization(
    status=OrganizationStatus.APPROVED,
):
    return SimpleNamespace(
        id=ORG_ID,
        status=status,
        name="Lucidex Institution",
        contact_email="institution@example.com",
        registrant_name="Test Registrant",
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
@pytest.mark.parametrize("role", ["super_admin", "operations_admin"])
@pytest.mark.parametrize(
    "frontend_base_url",
    ["https://frontend.example", "https://frontend.example/"],
)
async def test_admin_roles_approve_returns_invite_token_without_logging_it(
    monkeypatch,
    caplog,
    role,
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
        admin=fake_admin(role=role),
        request_id="approve-request",
    )

    assert len(rotate_calls) == 1
    assert sent[0]["email"] == "institution@example.com"
    assert sent[0]["context"]["invite_url"] == (
        "https://frontend.example/invite/setup-password?"
        "token=raw-secret-invite-token-1"
    )
    assert sent[0]["context"]["contact_email"] == "institution@example.com"
    assert "//invite" not in sent[0]["context"]["invite_url"]
    assert sent[0]["context"]["expires_in_hours"] == 72
    assert result.organization_status == OrganizationStatus.APPROVED
    assert result.invite_status == InviteStatus.PENDING
    assert result.email_sent is True
    assert result.invite_token == "raw-secret-invite-token-1"
    assert "token_hash" not in result.model_dump_json()
    assert "invite_url" not in result.model_dump_json()
    records = [
        record
        for record in caplog.records
        if record.getMessage() == "organization_approved_and_invited"
    ]
    assert [record.request_id for record in records] == ["approve-request"]
    assert [record.actor_role for record in records] == [role]
    assert all(record.organization_id == str(ORG_ID) for record in records)
    assert "raw-secret-invite-token" not in caplog.text
    assert "institution@example.com" not in caplog.text


@pytest.mark.parametrize(
    "payload",
    [None, {}, {"reason": ""}, {"reason": "   "}],
)
def test_reject_requires_reason_before_side_effects(
    monkeypatch,
    caplog,
    payload,
):
    caplog.set_level(logging.WARNING, logger="lucidex.exception")
    database_get = AsyncMock()
    send_email = AsyncMock()
    notification_insert = AsyncMock()
    audit_insert = AsyncMock()
    monkeypatch.setattr(organization_service.Organization, "get", database_get)
    monkeypatch.setattr(
        organization_service.mailer_service,
        "send_email",
        send_email,
    )
    monkeypatch.setattr(
        organization_service.Notification,
        "insert",
        notification_insert,
    )
    monkeypatch.setattr(
        organization_service.AuditLog,
        "insert",
        audit_insert,
    )

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(organizations_router, prefix="/api/v1")

    async def admin_override():
        return fake_admin()

    app.dependency_overrides[require_admin] = admin_override
    url = f"/api/v1/admin/organizations/{ORG_ID}/reject"
    client = TestClient(app)
    response = client.post(url) if payload is None else client.post(url, json=payload)

    assert response.status_code == 422
    assert response.json() == {
        "success": False,
        "data": None,
        "message": "A reason is required.",
        "error_code": "VALIDATION_ERROR",
    }
    database_get.assert_not_awaited()
    send_email.assert_not_awaited()
    notification_insert.assert_not_awaited()
    audit_insert.assert_not_awaited()
    record = next(
        record
        for record in caplog.records
        if record.name == "lucidex.exception"
        and record.getMessage() == "application_error"
    )
    assert record.actor_id == str(ADMIN_ID)
    assert record.actor_role == "super_admin"
    assert record.organization_id == str(ORG_ID)


@pytest.mark.asyncio
async def test_reject_success_creates_email_notification_and_audit(
    monkeypatch,
):
    reviewed_at = datetime.now(UTC)
    organization = fake_organization(status=OrganizationStatus.REJECTED)
    sent = []
    notifications = []
    audits = []

    async def decide(**_):
        return organization, reviewed_at

    async def send_email(**kwargs):
        sent.append(kwargs)

    async def insert_notification(self):
        notifications.append(self)
        return self

    async def insert_audit(self):
        audits.append(self)
        return self

    monkeypatch.setattr(
        organization_service,
        "_decide_pending_organization",
        decide,
    )
    monkeypatch.setattr(
        organization_service.mailer_service,
        "send_email",
        send_email,
    )
    monkeypatch.setattr(
        organization_service.Notification,
        "insert",
        insert_notification,
    )
    monkeypatch.setattr(
        organization_service.Notification,
        "get_motor_collection",
        classmethod(lambda cls: Mock()),
    )
    monkeypatch.setattr(
        organization_service.AuditLog,
        "insert",
        insert_audit,
    )
    monkeypatch.setattr(
        organization_service.AuditLog,
        "get_motor_collection",
        classmethod(lambda cls: Mock()),
    )

    result = await reject_organization(
        organization_id=ORG_ID,
        reason="  Required compliance documents were not provided.  ",
        admin=fake_admin(role="operations_admin"),
        request_id="reject-request-id",
    )

    reason = "Required compliance documents were not provided."
    assert result.organization_status == OrganizationStatus.REJECTED
    assert result.rejection_reason == reason
    assert result.reviewed_at == reviewed_at
    assert sent == [
        {
            "email": "institution@example.com",
            "template": EmailTemplate.APPLICATION_REJECTED,
            "context": {
                "registrant_name": "Test Registrant",
                "institution_name": "Lucidex Institution",
                "rejection_reason": reason,
            },
        }
    ]

    notification = notifications[0]
    assert notification.owner_id is None
    assert notification.organization_id == ORG_ID
    assert str(notification.contact_email) == "institution@example.com"
    assert notification.type == "application_rejected"
    assert reason in notification.message

    audit = audits[0]
    assert audit.actor_id == ADMIN_ID
    assert audit.actor_type == "admin"
    assert audit.action_type == "request_rejected"
    assert audit.timestamp == reviewed_at
    assert json.loads(audit.detail) == {
        "organization_id": str(ORG_ID),
        "request_id": "reject-request-id",
        "reason": reason,
    }


@pytest.mark.asyncio
async def test_rejection_email_failure_has_safe_domain_error(monkeypatch):
    organization = fake_organization(status=OrganizationStatus.REJECTED)
    notification_insert = AsyncMock()
    audit_insert = AsyncMock()
    monkeypatch.setattr(
        organization_service,
        "_decide_pending_organization",
        AsyncMock(return_value=(organization, datetime.now(UTC))),
    )
    monkeypatch.setattr(
        organization_service.mailer_service,
        "send_email",
        AsyncMock(side_effect=EmailDeliveryError()),
    )
    monkeypatch.setattr(
        organization_service.Notification,
        "insert",
        notification_insert,
    )
    monkeypatch.setattr(
        organization_service.AuditLog,
        "insert",
        audit_insert,
    )

    with pytest.raises(AppError) as exc_info:
        await reject_organization(
            organization_id=ORG_ID,
            reason="Missing documents",
            admin=fake_admin(),
        )

    error = exc_info.value
    assert error.status_code == 502
    assert error.error_code == "REJECTION_EMAIL_FAILED"
    assert error.message == "Rejection email failed."
    assert error.log_context["actor_id"] == str(ADMIN_ID)
    assert error.log_context["organization_id"] == str(ORG_ID)
    assert "Missing documents" not in str(error.log_context)
    notification_insert.assert_not_awaited()
    audit_insert.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejection_notification_failure_has_safe_domain_error(monkeypatch):
    organization = fake_organization(status=OrganizationStatus.REJECTED)
    notification_insert = AsyncMock(side_effect=RuntimeError("database unavailable"))
    audit_factory = Mock()
    monkeypatch.setattr(
        organization_service,
        "_decide_pending_organization",
        AsyncMock(return_value=(organization, datetime.now(UTC))),
    )
    monkeypatch.setattr(
        organization_service.mailer_service,
        "send_email",
        AsyncMock(),
    )
    monkeypatch.setattr(
        organization_service,
        "Notification",
        lambda **_: SimpleNamespace(insert=notification_insert),
    )
    monkeypatch.setattr(organization_service, "AuditLog", audit_factory)

    with pytest.raises(AppError) as exc_info:
        await reject_organization(
            organization_id=ORG_ID,
            reason="Missing documents",
            admin=fake_admin(),
        )

    error = exc_info.value
    assert error.status_code == 500
    assert error.error_code == "REJECTION_NOTIFICATION_FAILED"
    assert error.log_context["failure_reason"] == "RuntimeError"
    assert "database unavailable" not in str(error.log_context)
    audit_factory.assert_not_called()


@pytest.mark.asyncio
async def test_rejection_audit_failure_has_safe_domain_error(monkeypatch):
    organization = fake_organization(status=OrganizationStatus.REJECTED)
    notification_insert = AsyncMock()
    audit_insert = AsyncMock(side_effect=RuntimeError("database unavailable"))
    monkeypatch.setattr(
        organization_service,
        "_decide_pending_organization",
        AsyncMock(return_value=(organization, datetime.now(UTC))),
    )
    monkeypatch.setattr(
        organization_service.mailer_service,
        "send_email",
        AsyncMock(),
    )
    monkeypatch.setattr(
        organization_service,
        "Notification",
        lambda **_: SimpleNamespace(insert=notification_insert),
    )
    monkeypatch.setattr(
        organization_service,
        "AuditLog",
        lambda **_: SimpleNamespace(insert=audit_insert),
    )

    with pytest.raises(AppError) as exc_info:
        await reject_organization(
            organization_id=ORG_ID,
            reason="Missing documents",
            admin=fake_admin(),
        )

    error = exc_info.value
    assert error.status_code == 500
    assert error.error_code == "REJECTION_AUDIT_FAILED"
    assert error.log_context["failure_reason"] == "RuntimeError"
    assert "database unavailable" not in str(error.log_context)
    notification_insert.assert_awaited_once()


def test_rejection_email_subject_body_and_html_escaping():
    message = organization_service.mailer_service._build_message(
        "institution@example.com",
        EmailTemplate.APPLICATION_REJECTED,
        {
            "registrant_name": "Test Registrant",
            "institution_name": "Lucidex Institution",
            "rejection_reason": "Missing <script>alert('x')</script>",
        },
    )

    html = message.get_body(preferencelist=("html",)).get_content()
    assert message["Subject"] == "Update on Your Lucidex Application"
    assert "Cập nhật về hồ sơ đăng ký Lucidex của bạn" in html
    assert "Xin chào" in html
    assert "Lý do:" in html
    assert "Test Registrant" in html
    assert "Lucidex Institution" in html
    assert "Missing &lt;script&gt;alert" in html
    assert "<script>alert('x')</script>" not in html


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


def test_decision_has_no_edit_or_delete_api():
    app = FastAPI()
    app.include_router(organizations_router, prefix="/api/v1")

    operations = app.openapi()["paths"][
        "/api/v1/admin/organizations/{organization_id}/reject"
    ]

    assert "post" in operations
    assert "patch" not in operations
    assert "put" not in operations
    assert "delete" not in operations


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("existing_status", "decision"),
    [
        (OrganizationStatus.APPROVED, OrganizationStatus.APPROVED),
        (OrganizationStatus.APPROVED, OrganizationStatus.REJECTED),
        (OrganizationStatus.REJECTED, OrganizationStatus.REJECTED),
        (OrganizationStatus.REJECTED, OrganizationStatus.APPROVED),
    ],
)
async def test_final_decision_cannot_be_changed(
    monkeypatch,
    existing_status,
    decision,
):
    monkeypatch.setattr(
        organization_service.Organization,
        "get",
        AsyncMock(return_value=fake_organization(status=existing_status)),
    )
    find_one = Mock()
    monkeypatch.setattr(
        organization_service.Organization,
        "find_one",
        find_one,
    )

    with pytest.raises(AppError) as exc_info:
        await organization_service._decide_pending_organization(
            organization_id=ORG_ID,
            admin=fake_admin(),
            decision=decision,
            rejection_reason="Final reason",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "ORGANIZATION_DECISION_FINAL"
    find_one.assert_not_called()


@pytest.mark.asyncio
async def test_reject_transition_updates_required_fields_atomically(monkeypatch):
    pending = fake_organization(status=OrganizationStatus.PENDING_REVIEW)
    rejected = fake_organization(status=OrganizationStatus.REJECTED)
    update = AsyncMock(return_value=SimpleNamespace(modified_count=1))
    query = SimpleNamespace(update=update)
    monkeypatch.setattr(
        organization_service.Organization,
        "get",
        AsyncMock(side_effect=[pending, rejected]),
    )
    monkeypatch.setattr(
        organization_service.Organization,
        "find_one",
        Mock(return_value=query),
    )

    result, reviewed_at = await organization_service._decide_pending_organization(
        organization_id=ORG_ID,
        admin=fake_admin(role="operations_admin"),
        decision=OrganizationStatus.REJECTED,
        rejection_reason="Missing documents",
    )

    assert result is rejected
    values = update.await_args.args[0]["$set"]
    assert values == {
        "status": OrganizationStatus.REJECTED.value,
        "rejection_reason": "Missing documents",
        "reviewed_by": ADMIN_ID,
        "reviewed_at": reviewed_at,
    }


@pytest.mark.asyncio
async def test_second_approve_does_not_create_another_invitation(monkeypatch):
    rotate_invite = AsyncMock()
    monkeypatch.setattr(
        organization_service,
        "_approve_if_needed",
        AsyncMock(
            side_effect=AppError(
                status_code=409,
                message="Organization decision is final.",
                error_code="ORGANIZATION_DECISION_FINAL",
            )
        ),
    )
    monkeypatch.setattr(
        organization_service,
        "rotate_pending_invite",
        rotate_invite,
    )

    with pytest.raises(AppError) as exc_info:
        await approve_organization(
            organization_id=ORG_ID,
            admin=fake_admin(),
        )

    assert exc_info.value.error_code == "ORGANIZATION_DECISION_FINAL"
    rotate_invite.assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_reject_does_not_send_email_notification_or_audit(
    monkeypatch,
):
    final_error = AppError(
        status_code=409,
        message="Organization decision is final.",
        error_code="ORGANIZATION_DECISION_FINAL",
    )
    send_email = AsyncMock()
    notification_insert = AsyncMock()
    audit_insert = AsyncMock()
    monkeypatch.setattr(
        organization_service,
        "_decide_pending_organization",
        AsyncMock(side_effect=final_error),
    )
    monkeypatch.setattr(
        organization_service.mailer_service,
        "send_email",
        send_email,
    )
    monkeypatch.setattr(
        organization_service.Notification,
        "insert",
        notification_insert,
    )
    monkeypatch.setattr(
        organization_service.AuditLog,
        "insert",
        audit_insert,
    )

    with pytest.raises(AppError) as exc_info:
        await reject_organization(
            organization_id=ORG_ID,
            reason="Already decided",
            admin=fake_admin(),
        )

    assert exc_info.value is final_error
    send_email.assert_not_awaited()
    notification_insert.assert_not_awaited()
    audit_insert.assert_not_awaited()


@pytest.mark.asyncio
async def test_concurrent_approve_and_reject_only_one_decision_succeeds(
    monkeypatch,
):
    state = {
        "status": OrganizationStatus.PENDING_REVIEW,
        "rejection_reason": None,
        "reviewed_by": None,
        "reviewed_at": None,
    }

    def current_organization():
        organization = fake_organization(status=state["status"])
        organization.rejection_reason = state["rejection_reason"]
        organization.reviewed_by = state["reviewed_by"]
        organization.reviewed_at = state["reviewed_at"]
        return organization

    async def get_organization(_):
        return current_organization()

    class AtomicUpdateQuery:
        async def update(self, update):
            if state["status"] != OrganizationStatus.PENDING_REVIEW:
                return SimpleNamespace(modified_count=0)
            values = update["$set"]
            state.update(
                status=OrganizationStatus(values["status"]),
                rejection_reason=values["rejection_reason"],
                reviewed_by=values["reviewed_by"],
                reviewed_at=values["reviewed_at"],
            )
            await asyncio.sleep(0)
            return SimpleNamespace(modified_count=1)

    monkeypatch.setattr(
        organization_service.Organization,
        "get",
        get_organization,
    )
    monkeypatch.setattr(
        organization_service.Organization,
        "find_one",
        lambda _: AtomicUpdateQuery(),
    )

    outcomes = await asyncio.gather(
        organization_service._decide_pending_organization(
            organization_id=ORG_ID,
            admin=fake_admin(),
            decision=OrganizationStatus.APPROVED,
        ),
        organization_service._decide_pending_organization(
            organization_id=ORG_ID,
            admin=fake_admin(role="operations_admin"),
            decision=OrganizationStatus.REJECTED,
            rejection_reason="Missing documents",
        ),
        return_exceptions=True,
    )

    successes = [outcome for outcome in outcomes if not isinstance(outcome, Exception)]
    failures = [outcome for outcome in outcomes if isinstance(outcome, AppError)]
    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].error_code == "ORGANIZATION_DECISION_FINAL"


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


@pytest.mark.asyncio
async def test_list_organizations_filters_and_sorts_oldest_first(monkeypatch):
    from src.admin.services.organizations import list_organizations
    from src.organization.constants import OrganizationType

    sample_org_issuer = SimpleNamespace(
        id=ORG_ID,
        type=OrganizationType.ISSUER,
        status=OrganizationStatus.PENDING_REVIEW,
        name="Issuer Org",
        tax_code="0101234567",
        address="123 Street",
        legal_rep_name="Rep Name",
        contact_email="issuer@gmail.com",
        contact_phone="0901234567",
        registrant_name="Registrant",
        registrant_title="Manager",
        documents=[],
        rejection_reason=None,
        reviewed_by=None,
        reviewed_at=None,
        created_at=datetime.now(UTC),
    )

    captured_sort = []

    class DummyQuery:
        def sort(self, key):
            captured_sort.append(key)
            return self

        async def to_list(self):
            return [sample_org_issuer]

    captured_query = {}

    def fake_find(query):
        captured_query.update(query)
        return DummyQuery()

    monkeypatch.setattr(organization_service.Organization, "find", fake_find)

    res = await list_organizations(
        status=OrganizationStatus.PENDING_REVIEW,
        org_type=OrganizationType.ISSUER,
    )

    assert len(res) == 1
    assert res[0].id == str(ORG_ID)
    assert res[0].type == OrganizationType.ISSUER
    assert res[0].status == OrganizationStatus.PENDING_REVIEW
    assert captured_query == {"status": "pending_review", "type": "issuer"}
    assert captured_sort == ["created_at"]


@pytest.mark.asyncio
async def test_rejected_organization_is_not_returned_in_pending_list(monkeypatch):
    rejected = SimpleNamespace(status=OrganizationStatus.REJECTED)

    class DummyQuery:
        def __init__(self, organizations, query):
            self.organizations = organizations
            self.query = query

        def sort(self, _):
            return self

        async def to_list(self):
            return [
                organization
                for organization in self.organizations
                if organization.status.value == self.query["status"]
            ]

    monkeypatch.setattr(
        organization_service.Organization,
        "find",
        lambda query: DummyQuery([rejected], query),
    )

    organizations = await organization_service.list_organizations()

    assert organizations == []


