import json
import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from beanie import PydanticObjectId
from httpx import ASGITransport, AsyncClient

import src.admin.dependencies as admin_dependencies
import src.admin.routers.organizations as organization_router_module
from src.admin.dependencies import require_admin
from src.admin.exceptions import InvalidAuthenticationCodeError
from src.admin.services import admin_auth_service
from src.auth.constants import ActorType, SessionStatus
from src.auth.services import create_access_token
from src.exceptions import AppError
from src.logging import JsonFormatter
from src.main import app

ADMIN_ID = PydanticObjectId("507f1f77bcf86cd799439012")
SESSION_ID = PydanticObjectId("507f1f77bcf86cd799439014")
ADMIN_ACCESS_ERROR = {
    "success": False,
    "data": None,
    "message": "Invalid or expired admin access token.",
    "error_code": "INVALID_ADMIN_ACCESS_TOKEN",
}


@pytest.fixture(autouse=True)
async def otp_test_database():
    """Override the root MongoDB fixture; these API tests use test doubles."""
    yield


@pytest.fixture(scope="session", autouse=True)
def _drop_test_database_at_session_end():
    yield


@pytest.fixture
async def client():
    app.dependency_overrides.clear()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as value:
            yield value
    finally:
        app.dependency_overrides.clear()


def _event_records(caplog, logger_name: str, event: str):
    return [
        record
        for record in caplog.records
        if record.name == logger_name and record.getMessage() == event
    ]


def _assert_safe_401_logs(caplog, *, path: str, secret: str | None = None):
    application_records = _event_records(
        caplog, "lucidex.exception", "application_error"
    )
    assert len(application_records) == 1
    application_record = application_records[0]
    assert application_record.levelno == logging.WARNING
    assert application_record.exc_info is None

    payload = json.loads(JsonFormatter().format(application_record))
    assert payload["method"] == "POST"
    assert payload["path"] == path
    assert payload["status_code"] == 401
    assert payload["error_code"] in {
        "INVALID_ADMIN_ACCESS_TOKEN",
        "INVALID_ADMIN_CREDENTIALS",
        "INVALID_AUTHENTICATION_CODE",
    }
    assert payload["message"] in {
        "Invalid or expired admin access token.",
        "Invalid username or password.",
        "Invalid code. Please try again.",
    }
    assert payload["request_id"]
    assert "exception" not in payload

    request_records = _event_records(caplog, "lucidex.request", "http_request")
    assert len(request_records) == 1
    assert request_records[0].status_code == 401
    assert request_records[0].levelno == logging.WARNING
    assert request_records[0].request_id == payload["request_id"]

    serialized = json.dumps(payload)
    if secret is not None:
        assert secret not in serialized
    assert "Authorization" not in serialized
    assert "Traceback" not in serialized


@pytest.mark.asyncio
async def test_missing_admin_authorization_is_handled_as_401(client, caplog):
    caplog.set_level(logging.INFO)

    response = await client.post("/api/v1/admin/accounts")

    assert response.status_code == 401
    assert response.json() == ADMIN_ACCESS_ERROR
    _assert_safe_401_logs(
        caplog,
        path="/api/v1/admin/accounts",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("token_kind", ["invalid", "expired"])
async def test_invalid_or_expired_admin_token_is_handled_as_401(
    client,
    caplog,
    token_kind,
):
    caplog.set_level(logging.INFO)
    if token_kind == "invalid":
        token = "invalid-secret-admin-access-token"
    else:
        token = create_access_token(
            subject=str(ADMIN_ID),
            actor_type=ActorType.PLATFORM_ADMIN,
            session_id=str(SESSION_ID),
            expires_delta=timedelta(seconds=-1),
        )

    response = await client.post(
        "/api/v1/admin/accounts",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json() == ADMIN_ACCESS_ERROR
    _assert_safe_401_logs(
        caplog,
        path="/api/v1/admin/accounts",
        secret=token,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("session_state", ["inactive", "expired"])
async def test_invalid_admin_session_is_handled_as_401(
    client,
    caplog,
    monkeypatch,
    session_state,
):
    caplog.set_level(logging.INFO)
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    status = SessionStatus.ACTIVE
    if session_state == "inactive":
        status = SessionStatus.REVOKED
    else:
        expires_at = datetime.now(UTC) - timedelta(seconds=1)

    session = SimpleNamespace(
        actor_id=ADMIN_ID,
        actor_type=ActorType.PLATFORM_ADMIN,
        status=status,
        twofa_verified=True,
        expires_at=expires_at,
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

    monkeypatch.setattr(admin_dependencies.Session, "get", get_session)
    token = "session-state-secret-token"

    response = await client.post(
        "/api/v1/admin/accounts",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json() == ADMIN_ACCESS_ERROR
    _assert_safe_401_logs(
        caplog,
        path="/api/v1/admin/accounts",
        secret=token,
    )


@pytest.mark.asyncio
async def test_invalid_admin_credentials_subclass_is_handled_as_401(
    client,
    caplog,
    monkeypatch,
):
    caplog.set_level(logging.INFO)

    async def get_by_username(_):
        return None

    monkeypatch.setattr(
        admin_auth_service._repository,
        "get_by_username",
        get_by_username,
    )
    password = "secret-password-that-must-not-be-logged"

    response = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": "missing-admin", "password": password},
    )

    assert response.status_code == 401
    assert response.json() == {
        "success": False,
        "data": None,
        "message": "Invalid username or password.",
        "error_code": "INVALID_ADMIN_CREDENTIALS",
    }
    assert "Traceback" not in response.text
    _assert_safe_401_logs(
        caplog,
        path="/api/v1/admin/auth/login",
        secret=password,
    )


@pytest.mark.asyncio
async def test_invalid_admin_totp_subclass_is_handled_as_401(
    client,
    caplog,
    monkeypatch,
):
    caplog.set_level(logging.INFO)

    async def reject_totp(**_):
        raise InvalidAuthenticationCodeError("Invalid code. Please try again.")

    monkeypatch.setattr(admin_auth_service, "verify_login", reject_totp)
    challenge_token = "secret-challenge-token"
    otp_code = "123456"

    response = await client.post(
        "/api/v1/admin/auth/totp/login/verify",
        json={"challenge_token": challenge_token, "otp_code": otp_code},
    )

    assert response.status_code == 401
    assert response.json() == {
        "success": False,
        "data": None,
        "message": "Invalid code. Please try again.",
        "error_code": "INVALID_AUTHENTICATION_CODE",
    }
    _assert_safe_401_logs(
        caplog,
        path="/api/v1/admin/auth/totp/login/verify",
        secret=challenge_token,
    )
    serialized_logs = "\n".join(
        JsonFormatter().format(record)
        for record in caplog.records
        if record.name.startswith("lucidex.")
    )
    assert otp_code not in serialized_logs


@pytest.mark.asyncio
async def test_unexpected_exception_returns_safe_500_and_logs_traceback(
    client,
    caplog,
    monkeypatch,
):
    caplog.set_level(logging.INFO)

    async def fail_login(**_):
        raise RuntimeError("internal database detail")

    monkeypatch.setattr(admin_auth_service, "login", fail_login)

    response = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret-password"},
    )

    assert response.status_code == 500
    assert response.json() == {
        "success": False,
        "data": None,
        "message": "An unexpected error occurred.",
        "error_code": "INTERNAL_SERVER_ERROR",
    }
    assert "internal database detail" not in response.text
    assert "Traceback" not in response.text

    records = _event_records(caplog, "lucidex.exception", "unhandled_exception")
    assert len(records) == 1
    assert records[0].levelno == logging.ERROR
    assert records[0].exc_info is not None


@pytest.mark.asyncio
async def test_approve_app_error_logs_safe_context_once(
    client,
    caplog,
    monkeypatch,
):
    caplog.set_level(logging.INFO)
    admin = SimpleNamespace(
        id=ADMIN_ID,
        role="operations_admin",
        status="active",
    )

    async def authenticated_admin():
        return admin

    async def fail_approval(**_):
        raise AppError(
            status_code=502,
            message="Organization was approved, but the invitation email failed.",
            error_code="INVITATION_EMAIL_FAILED",
            log_context={
                "actor_id": str(ADMIN_ID),
                "actor_role": "operations_admin",
                "organization_id": "507f1f77bcf86cd799439011",
                "invite_id": "507f1f77bcf86cd799439013",
                "failure_reason": "EmailDeliveryError",
                "access_token": "must-not-be-accepted-as-log-context",
            },
        )

    app.dependency_overrides[require_admin] = authenticated_admin
    monkeypatch.setattr(
        organization_router_module,
        "approve_organization",
        fail_approval,
    )

    response = await client.post(
        "/api/v1/admin/organizations/507f1f77bcf86cd799439011/approve",
        headers={"Authorization": "Bearer secret-access-token"},
    )

    assert response.status_code == 502
    records = _event_records(caplog, "lucidex.exception", "application_error")
    assert len(records) == 1
    record = records[0]
    assert record.levelno == logging.ERROR
    assert record.exc_info is None
    assert record.actor_id == str(ADMIN_ID)
    assert record.actor_role == "operations_admin"
    assert record.organization_id == "507f1f77bcf86cd799439011"
    assert record.invite_id == "507f1f77bcf86cd799439013"
    assert record.failure_reason == "EmailDeliveryError"
    serialized = JsonFormatter().format(record)
    assert "secret-access-token" not in serialized
    assert "must-not-be-accepted-as-log-context" not in serialized
