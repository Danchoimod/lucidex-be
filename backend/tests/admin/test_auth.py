import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
import pytest

import src.admin.services.auth as auth_module
from src.admin.constants import AdminTokenPurpose
from src.admin.exceptions import (
    InvalidAdminCredentialsError,
    InvalidAdminTokenError,
    InvalidAuthenticationCodeError,
)
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


@pytest.mark.asyncio
async def test_unknown_username_and_wrong_password_have_same_error(auth_context):
    service, _, _, _, _ = auth_context

    with pytest.raises(InvalidAdminCredentialsError) as unknown:
        await service.login(username="missing", password="correct-password")
    with pytest.raises(InvalidAdminCredentialsError) as wrong_password:
        await service.login(username="superadmin", password="wrong-password")

    assert unknown.value.message == wrong_password.value.message
    assert unknown.value.message == "Invalid login credentials."


@pytest.mark.asyncio
async def test_password_login_does_not_create_session(auth_context):
    service, _, _, session_calls, _ = auth_context

    await service.login(username="superadmin", password="correct-password")

    assert session_calls == []


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

    with pytest.raises(InvalidAuthenticationCodeError):
        await service.verify_setup(setup_token=token, otp_code="000000")

    assert session_calls == []


@pytest.mark.asyncio
async def test_valid_totp_setup_creates_verified_session(
    auth_context, monkeypatch
):
    service, _, admin, session_calls, sessions = auth_context
    admin.totp_secret = "JBSWY3DPEHPK3PXP"
    token = create_admin_temp_token(admin.id, AdminTokenPurpose.TOTP_SETUP)
    monkeypatch.setattr(auth_module, "verify_totp", lambda *_: True)

    result = await service.verify_setup(setup_token=token, otp_code="123456")

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


@pytest.mark.asyncio
async def test_login_after_setup_returns_only_challenge_token(auth_context):
    service, _, admin, session_calls, _ = auth_context
    admin.twofa_enabled = True
    admin.totp_secret = "JBSWY3DPEHPK3PXP"

    result = await service.login(
        username="superadmin", password="correct-password"
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


@pytest.mark.asyncio
async def test_invalid_totp_login_does_not_create_session(
    auth_context, monkeypatch
):
    service, _, admin, session_calls, _ = auth_context
    admin.twofa_enabled = True
    admin.totp_secret = "JBSWY3DPEHPK3PXP"
    token = create_admin_temp_token(admin.id, AdminTokenPurpose.LOGIN_2FA)
    monkeypatch.setattr(auth_module, "verify_totp", lambda *_: False)

    with pytest.raises(InvalidAuthenticationCodeError):
        await service.verify_login(challenge_token=token, otp_code="000000")

    assert session_calls == []


@pytest.mark.asyncio
async def test_valid_totp_login_creates_verified_session(
    auth_context, monkeypatch
):
    service, _, admin, session_calls, sessions = auth_context
    admin.twofa_enabled = True
    admin.totp_secret = "JBSWY3DPEHPK3PXP"
    token = create_admin_temp_token(admin.id, AdminTokenPurpose.LOGIN_2FA)
    monkeypatch.setattr(auth_module, "verify_totp", lambda *_: True)

    result = await service.verify_login(
        challenge_token=token,
        otp_code="123456",
    )

    assert result.access_token == "access-token"
    assert len(session_calls) == 1
    assert sessions[0].twofa_verified is True
    assert sessions[0].save_count == 1


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
