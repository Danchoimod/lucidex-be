import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
import pyotp
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.admin.routers.super_auth as auth_router_module
import src.admin.services.auth as auth_module
from src.admin.constants import AdminTokenPurpose
from src.admin.exceptions import (
    InvalidAdminCredentialsError,
    InvalidAdminTokenError,
    InvalidAuthenticationCodeError,
)
from src.admin.routers.super_auth import router as admin_auth_router
from src.admin.services.auth import AdminAuthService
from src.admin.utils import (
    JWT_ALGORITHM,
    create_admin_temp_token,
    create_qr_data_url,
)
from src.auth.constants import ActorType
from src.config import settings


@pytest.fixture(autouse=True)
async def otp_test_database():
    """Override the root MongoDB fixture; Admin auth tests are unit tests."""
    yield


@pytest.fixture(scope="session", autouse=True)
def _drop_test_database_at_session_end():
    """Prevent the root test fixture from dropping an external database."""
    yield


@dataclass
class FakeAdmin:
    id: str = "admin-id"
    username: str = "superadmin"
    password_hash: str = "password-hash"
    role: str | None = "super_admin"
    twofa_method: str = "totp"
    twofa_enabled: bool = False
    totp_secret: str | None = None
    status: str = "active"


class FakeRepository:
    def __init__(self, admin: FakeAdmin | None) -> None:
        self.admin = admin

    async def get_by_username(self, username: str):
        if self.admin and username == self.admin.username:
            return self.admin
        return None

    async def get_by_id(self, admin_id: str):
        if self.admin and admin_id == str(self.admin.id):
            return self.admin
        return None

    async def set_totp_secret_if_missing(self, admin, secret: str):
        if admin.totp_secret is None:
            admin.totp_secret = secret
        return admin

    async def enable_twofa(self, admin) -> bool:
        if admin.twofa_enabled:
            return False
        admin.twofa_enabled = True
        return True


@dataclass
class FakeSession:
    id: str = "session-id"
    twofa_verified: bool = False
    save_count: int = 0

    async def save(self) -> None:
        self.save_count += 1


@pytest.fixture
def auth_context(monkeypatch):
    admin = FakeAdmin()
    repository = FakeRepository(admin)
    service = AdminAuthService(repository)  # type: ignore[arg-type]
    session_calls: list[dict] = []
    sessions: list[FakeSession] = []

    async def create_session(**kwargs):
        session_calls.append(kwargs)
        session = FakeSession()
        sessions.append(session)
        return session, "raw-refresh-token-must-not-leak"

    monkeypatch.setattr(
        auth_module,
        "verify_password",
        lambda password, password_hash: (
            password == "correct-password" and password_hash == "password-hash"
        ),
    )
    monkeypatch.setattr(
        auth_module.session_service,
        "create_session",
        create_session,
    )
    monkeypatch.setattr(
        auth_module,
        "create_access_token",
        lambda **_: "access-token",
    )

    return service, repository, admin, session_calls, sessions


@pytest.fixture
def admin_auth_app() -> FastAPI:
    app = FastAPI()
    app.include_router(admin_auth_router, prefix="/api/v1")
    return app


@pytest.mark.asyncio
async def test_unknown_username_and_wrong_password_have_same_error(auth_context):
    service, _, _, _, _ = auth_context

    with pytest.raises(InvalidAdminCredentialsError) as unknown:
        await service.login(username="missing", password="correct-password")
    with pytest.raises(InvalidAdminCredentialsError) as wrong_password:
        await service.login(username="superadmin", password="wrong-password")

    assert unknown.value.message == wrong_password.value.message
    assert unknown.value.message == "Invalid username or password."


@pytest.mark.asyncio
async def test_password_login_does_not_create_session(auth_context, caplog):
    caplog.set_level("INFO", logger="lucidex.admin.auth")
    service, _, admin, session_calls, _ = auth_context

    result = await service.login(
        username="superadmin",
        password="correct-password",
        request_id="setup-challenge-request",
    )

    assert session_calls == []
    record = next(
        record
        for record in caplog.records
        if record.getMessage() == "admin_totp_setup_challenge_issued"
    )
    assert record.request_id == "setup-challenge-request"
    assert record.actor_id == admin.id
    assert record.actor_role == "super_admin"
    assert record.auth_stage == "totp_setup_required"
    assert result.setup_token not in caplog.text
    assert admin.totp_secret not in caplog.text


def test_admin_auth_openapi_descriptions_are_qa_ready(admin_auth_app):
    paths = admin_auth_app.openapi()["paths"]
    login = paths["/api/v1/admin/auth/login"]["post"]
    setup = paths["/api/v1/admin/auth/totp/setup/verify"]["post"]
    verify = paths["/api/v1/admin/auth/totp/login/verify"]["post"]

    assert "Super Admin or Operations Admin" in login["description"]
    assert "INVALID_ADMIN_CREDENTIALS" in login["responses"]["401"]["description"]
    assert "first-time TOTP enrollment" in setup["description"]
    assert "INVALID_ADMIN_TOKEN" in setup["responses"]["401"]["description"]
    assert "bearer access token" in verify["description"]
    assert "INVALID_AUTHENTICATION_CODE" in verify["responses"]["401"][
        "description"
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "twofa_method"),
    [
        (None, "totp"),
        ("super_admin", "email"),
        ("super_admin", "sms"),
    ],
)
async def test_login_rejects_missing_role_and_legacy_twofa_methods(
    auth_context,
    role,
    twofa_method,
):
    service, _, admin, session_calls, _ = auth_context
    admin.role = role
    admin.twofa_method = twofa_method

    with pytest.raises(InvalidAdminCredentialsError) as exc_info:
        await service.login(
            username="superadmin",
            password="correct-password",
        )

    serialized = str(
        {
            "message": exc_info.value.message,
            "error_code": exc_info.value.error_code,
        }
    )
    assert session_calls == []
    for field in (
        "setup_token",
        "challenge_token",
        "manual_entry_key",
        "totp_uri",
        "totp_secret",
    ):
        assert field not in serialized


@pytest.mark.asyncio
async def test_repeated_login_reuses_pending_totp_secret(auth_context):
    service, _, _, _, _ = auth_context

    first = await service.login(
        username="superadmin", password="correct-password"
    )
    second = await service.login(
        username="superadmin", password="correct-password"
    )

    assert first.manual_entry_key == second.manual_entry_key
    assert first.totp_uri == second.totp_uri
    assert first.qr_code == second.qr_code
    assert first.requires_totp_setup is True
    assert second.requires_totp_setup is True


def test_qr_data_url_contains_png():
    qr_code = create_qr_data_url(
        "otpauth://totp/Lucidex:root-admin?secret=TEST&issuer=Lucidex"
    )

    prefix = "data:image/png;base64,"
    assert qr_code.startswith(prefix)
    assert base64.b64decode(qr_code.removeprefix(prefix)).startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_expired_setup_token_is_rejected(auth_context):
    service, _, admin, _, _ = auth_context
    admin.totp_secret = "JBSWY3DPEHPK3PXP"
    token = create_admin_temp_token(
        admin.id,
        AdminTokenPurpose.TOTP_SETUP,
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(InvalidAdminTokenError):
        await service.verify_setup(setup_token=token, otp_code="123456")


@pytest.mark.asyncio
async def test_expired_login_challenge_is_rejected_without_session(auth_context):
    service, _, admin, session_calls, _ = auth_context
    admin.twofa_enabled = True
    admin.totp_secret = "JBSWY3DPEHPK3PXP"
    token = create_admin_temp_token(
        admin.id,
        AdminTokenPurpose.LOGIN_2FA,
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(InvalidAdminTokenError) as exc_info:
        await service.verify_login(
            challenge_token=token,
            otp_code="123456",
        )

    assert exc_info.value.error_code == "INVALID_ADMIN_TOKEN"
    assert session_calls == []
    assert "access_token" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_setup_token_without_exp_is_rejected(auth_context):
    service, _, admin, session_calls, _ = auth_context
    admin.totp_secret = "JBSWY3DPEHPK3PXP"
    token = jwt.encode(
        {
            "sub": admin.id,
            "actor_type": ActorType.PLATFORM_ADMIN,
            "purpose": AdminTokenPurpose.TOTP_SETUP,
        },
        settings.JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(InvalidAdminTokenError):
        await service.verify_setup(setup_token=token, otp_code="123456")

    assert session_calls == []
    assert admin.twofa_enabled is False


@pytest.mark.asyncio
async def test_setup_token_with_wrong_actor_type_is_rejected(
    auth_context, monkeypatch
):
    service, _, admin, session_calls, _ = auth_context
    admin.totp_secret = "JBSWY3DPEHPK3PXP"
    token = jwt.encode(
        {
            "sub": admin.id,
            "actor_type": ActorType.OWNER,
            "purpose": AdminTokenPurpose.TOTP_SETUP,
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        settings.JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    totp_calls = []
    monkeypatch.setattr(
        auth_module,
        "verify_totp",
        lambda *_: totp_calls.append(True) or True,
    )

    with pytest.raises(InvalidAdminTokenError):
        await service.verify_setup(setup_token=token, otp_code="123456")

    assert totp_calls == []
    assert session_calls == []


@pytest.mark.asyncio
async def test_setup_token_with_unknown_purpose_is_rejected(auth_context):
    service, _, admin, _, _ = auth_context
    admin.totp_secret = "JBSWY3DPEHPK3PXP"
    token = create_admin_temp_token(admin.id, "wrong-purpose")  # type: ignore[arg-type]

    with pytest.raises(InvalidAdminTokenError):
        await service.verify_setup(setup_token=token, otp_code="123456")


@pytest.mark.asyncio
async def test_challenge_token_cannot_verify_setup(auth_context):
    service, _, admin, _, _ = auth_context
    admin.totp_secret = "JBSWY3DPEHPK3PXP"
    token = create_admin_temp_token(admin.id, AdminTokenPurpose.LOGIN_2FA)

    with pytest.raises(InvalidAdminTokenError):
        await service.verify_setup(setup_token=token, otp_code="123456")


@pytest.mark.asyncio
async def test_setup_token_cannot_verify_login(auth_context):
    service, _, admin, _, _ = auth_context
    admin.twofa_enabled = True
    admin.totp_secret = "JBSWY3DPEHPK3PXP"
    token = create_admin_temp_token(admin.id, AdminTokenPurpose.TOTP_SETUP)

    with pytest.raises(InvalidAdminTokenError):
        await service.verify_login(challenge_token=token, otp_code="123456")


@pytest.mark.asyncio
async def test_invalid_totp_setup_does_not_create_session(
    auth_context, monkeypatch
):
    service, _, admin, session_calls, _ = auth_context
    admin.totp_secret = "JBSWY3DPEHPK3PXP"
    token = create_admin_temp_token(admin.id, AdminTokenPurpose.TOTP_SETUP)
    monkeypatch.setattr(auth_module, "verify_totp", lambda *_: False)

    with pytest.raises(InvalidAuthenticationCodeError) as exc_info:
        await service.verify_setup(setup_token=token, otp_code="000000")

    assert (
        exc_info.value.message
        == "Invalid authentication code."
    )
    assert session_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["super_admin", "operations_admin"])
async def test_supported_admin_roles_setup_totp_and_receive_access_token(
    auth_context, monkeypatch, caplog, role
):
    caplog.set_level("INFO", logger="lucidex.admin.auth")
    service, _, admin, session_calls, sessions = auth_context
    admin.role = role
    admin.totp_secret = "JBSWY3DPEHPK3PXP"
    token = create_admin_temp_token(admin.id, AdminTokenPurpose.TOTP_SETUP)
    monkeypatch.setattr(auth_module, "verify_totp", lambda *_: True)

    result = await service.verify_setup(
        setup_token=token,
        otp_code="123456",
        request_id="totp-setup-request",
    )

    assert result.model_dump() == {
        "access_token": "access-token",
        "token_type": "bearer",
    }
    assert session_calls == [
        {
            "actor_id": admin.id,
            "actor_type": ActorType.PLATFORM_ADMIN,
            "device_info": None,
        }
    ]
    assert sessions[0].twofa_verified is True
    assert sessions[0].save_count == 1
    record = next(
        record
        for record in caplog.records
        if record.getMessage() == "admin_totp_setup_verified"
    )
    assert record.request_id == "totp-setup-request"
    assert record.actor_id == admin.id
    assert record.actor_role == role
    assert record.auth_stage == "totp_setup_verified"
    assert token not in caplog.text
    assert "123456" not in caplog.text
    assert admin.totp_secret not in caplog.text


@pytest.mark.asyncio
async def test_login_after_setup_returns_only_challenge_token(auth_context, caplog):
    caplog.set_level("INFO", logger="lucidex.admin.auth")
    service, _, admin, session_calls, _ = auth_context
    admin.twofa_enabled = True
    admin.totp_secret = "JBSWY3DPEHPK3PXP"

    result = await service.login(
        username="superadmin",
        password="correct-password",
        request_id="login-challenge-request",
    )
    response = result.model_dump(exclude_none=True)

    assert response["requires_totp"] is True
    assert set(response) == {"requires_totp", "challenge_token"}
    assert "manual_entry_key" not in response
    assert "totp_uri" not in response
    assert "qr_code" not in response
    assert "setup_token" not in response
    assert "totp_secret" not in response
    assert session_calls == []
    record = next(
        record
        for record in caplog.records
        if record.getMessage() == "admin_login_challenge_issued"
    )
    assert record.request_id == "login-challenge-request"
    assert record.actor_id == admin.id
    assert record.actor_role == "super_admin"
    assert record.auth_stage == "totp_login_required"
    assert response["challenge_token"] not in caplog.text
    assert admin.totp_secret not in caplog.text


@pytest.mark.asyncio
async def test_invalid_totp_login_does_not_create_session(
    auth_context, monkeypatch
):
    service, _, admin, session_calls, _ = auth_context
    admin.twofa_enabled = True
    admin.totp_secret = "JBSWY3DPEHPK3PXP"
    token = create_admin_temp_token(admin.id, AdminTokenPurpose.LOGIN_2FA)
    monkeypatch.setattr(auth_module, "verify_totp", lambda *_: False)

    with pytest.raises(InvalidAuthenticationCodeError) as exc_info:
        await service.verify_login(challenge_token=token, otp_code="000000")

    assert exc_info.value.message == "Invalid authentication code."
    assert exc_info.value.status_code == 401
    assert exc_info.value.error_code == "INVALID_AUTHENTICATION_CODE"
    assert session_calls == []


@pytest.mark.asyncio
async def test_same_totp_secret_verifies_after_device_change(auth_context):
    service, _, admin, session_calls, sessions = auth_context
    original_secret = "JBSWY3DPEHPK3PXP"
    admin.twofa_enabled = True
    admin.totp_secret = original_secret
    token = create_admin_temp_token(admin.id, AdminTokenPurpose.LOGIN_2FA)
    otp_code = pyotp.TOTP(original_secret).now()

    result = await service.verify_login(
        challenge_token=token,
        otp_code=otp_code,
    )

    assert result.access_token == "access-token"
    assert admin.totp_secret == original_secret
    assert len(session_calls) == 1
    assert sessions[0].twofa_verified is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"challenge_token": "token", "otp_code": "12345"},
        {"challenge_token": "token", "otp_code": "1234567"},
        {"challenge_token": "token", "otp_code": "12a456"},
        {"challenge_token": "token"},
    ],
)
async def test_login_verify_rejects_malformed_otp_before_service(
    admin_auth_app,
    monkeypatch,
    payload,
):
    service_calls = []

    async def verify_login(**kwargs):
        service_calls.append(kwargs)
        pytest.fail("Malformed OTP must not reach the auth service.")

    monkeypatch.setattr(
        auth_router_module.admin_auth_service,
        "verify_login",
        verify_login,
    )

    async with AsyncClient(
        transport=ASGITransport(app=admin_auth_app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/admin/auth/totp/login/verify",
            json=payload,
        )

    assert response.status_code == 422
    assert service_calls == []


@pytest.mark.asyncio
async def test_valid_totp_login_creates_verified_session(
    auth_context, monkeypatch, caplog
):
    caplog.set_level("INFO", logger="lucidex.admin.auth")
    service, _, admin, session_calls, sessions = auth_context
    admin.twofa_enabled = True
    admin.totp_secret = "JBSWY3DPEHPK3PXP"
    token = create_admin_temp_token(admin.id, AdminTokenPurpose.LOGIN_2FA)
    monkeypatch.setattr(auth_module, "verify_totp", lambda *_: True)

    result = await service.verify_login(
        challenge_token=token,
        otp_code="123456",
        request_id="totp-login-request",
    )

    assert result.access_token == "access-token"
    assert len(session_calls) == 1
    assert sessions[0].twofa_verified is True
    assert sessions[0].save_count == 1
    record = next(
        record
        for record in caplog.records
        if record.getMessage() == "admin_totp_login_verified"
    )
    assert record.request_id == "totp-login-request"
    assert record.actor_id == admin.id
    assert record.actor_role == "super_admin"
    assert record.auth_stage == "totp_login_verified"
    assert token not in caplog.text
    assert "123456" not in caplog.text
    assert admin.totp_secret not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("username", "password"),
    [("missing", "correct-password"), ("superadmin", "wrong-password")],
)
async def test_invalid_login_does_not_leak_totp_data(
    auth_context,
    username,
    password,
):
    service, _, _, _, _ = auth_context

    with pytest.raises(InvalidAdminCredentialsError) as exc_info:
        await service.login(username=username, password=password)

    error_payload = {
        "message": exc_info.value.message,
        "error_code": exc_info.value.error_code,
    }
    serialized = str(error_payload)
    for field in (
        "setup_token",
        "challenge_token",
        "manual_entry_key",
        "totp_uri",
        "qr_code",
    ):
        assert field not in serialized
