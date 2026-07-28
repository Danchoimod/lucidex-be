from dataclasses import dataclass
from time import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError

import src.auth.services.login as login_module
import src.owner.services.oauth_auth as owner_oauth_module
from src.auth.constants import ActorType
from src.auth.exceptions import GoogleAccountPasswordLoginNotAllowedError
from src.auth.services.login import LoginService
from src.config import settings
from src.mailer import EmailDeliveryError, mailer_service
from src.main import app
from src.oauth.exceptions import OAuthEmailNotVerifiedError, OAuthVerificationError
from src.oauth.providers.google import GoogleOAuthProvider
from src.oauth.schemas import OAuthIdentity
from src.owner.constants import OwnerStatus
from src.owner.exceptions import (
    GoogleAccountMismatchError,
    GoogleEmailNotVerifiedError,
    InvalidGoogleTokenError,
    PasswordAccountOAuthLoginError,
)
from src.owner.services.oauth_auth import OwnerOAuthAuthService


@pytest.fixture(autouse=True)
async def otp_test_database():
    """Override the root MongoDB fixture; OAuth tests are isolated unit tests."""
    yield


@pytest.fixture(scope="session", autouse=True)
def _drop_test_database_at_session_end():
    yield


@dataclass
class FakeOwner:
    id: str = "owner-id"
    email: str = "owner@example.com"
    password_hash: str | None = None
    oauth_provider: str | None = "google"
    oauth_subject_id: str | None = "google-subject"
    full_name: str | None = "Owner Example"
    status: OwnerStatus = OwnerStatus.ACTIVE


class FakeOAuthService:
    def __init__(self, identity: OAuthIdentity | None = None) -> None:
        self.identity = identity or google_identity()
        self.error: Exception | None = None

    async def verify_google(self, credential: str) -> OAuthIdentity:
        if self.error:
            raise self.error
        return self.identity


class FakeRepository:
    def __init__(self, owner: FakeOwner | None = None) -> None:
        self.owner = owner
        self.created: list[dict] = []

    async def get_by_email(self, email: str):
        if self.owner and self.owner.email == email:
            return self.owner
        return None

    async def get_by_oauth_identity(self, provider: str, provider_subject: str):
        if (
            self.owner
            and self.owner.oauth_provider == provider
            and self.owner.oauth_subject_id == provider_subject
        ):
            return self.owner
        return None

    async def create_google_owner(self, **kwargs):
        self.created.append(kwargs)
        self.owner = FakeOwner(
            email=kwargs["email"],
            oauth_subject_id=kwargs["provider_subject"],
        )
        return self.owner


class FakeSessionService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create_session(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(id="session-id"), "refresh-token"


def google_identity() -> OAuthIdentity:
    return OAuthIdentity(
        provider="google",
        provider_subject="google-subject",
        email="owner@example.com",
        display_name="Owner Example",
        avatar_url="https://example.com/avatar.png",
    )


def build_service(
    owner: FakeOwner | None = None,
    identity: OAuthIdentity | None = None,
):
    repository = FakeRepository(owner)
    oauth = FakeOAuthService(identity)
    sessions = FakeSessionService()
    service = OwnerOAuthAuthService(
        repository=repository,  # type: ignore[arg-type]
        oauth=oauth,  # type: ignore[arg-type]
        sessions=sessions,  # type: ignore[arg-type]
    )
    return service, repository, oauth, sessions


@pytest.mark.asyncio
async def test_new_google_owner_creates_active_account_and_session(
    monkeypatch,
    caplog,
):
    service, repository, _, sessions = build_service()
    scheduled = []
    monkeypatch.setattr(owner_oauth_module, "create_access_token", Mock(return_value="access-token"))
    caplog.set_level("INFO", logger="lucidex.owner.oauth")

    owner, access_token, refresh_token = await service.login_with_google(
        "verified-google-token",
        request_id="signup-request-id",
        on_owner_created=scheduled.append,
    )

    assert owner.password_hash is None
    assert owner.oauth_provider == "google"
    assert owner.oauth_subject_id == "google-subject"
    assert owner.status == OwnerStatus.ACTIVE
    assert len(repository.created) == 1
    assert len(sessions.calls) == 1
    assert sessions.calls[0]["actor_type"] == ActorType.OWNER
    assert access_token == "access-token"
    assert refresh_token == "refresh-token"
    assert scheduled == [owner]
    record = next(
        record
        for record in caplog.records
        if record.message == "owner_google_signup_succeeded"
    )
    assert record.request_id == "signup-request-id"
    assert record.actor_id == "owner-id"
    assert record.actor_type == ActorType.OWNER
    assert record.auth_stage == "google_signup"
    assert "verified-google-token" not in caplog.text
    assert "google-subject" not in caplog.text


@pytest.mark.asyncio
async def test_existing_google_owner_is_not_duplicated(monkeypatch, caplog):
    service, repository, _, sessions = build_service(FakeOwner())
    scheduled = []
    monkeypatch.setattr(owner_oauth_module, "create_access_token", Mock(return_value="access-token"))
    caplog.set_level("INFO", logger="lucidex.owner.oauth")

    await service.login_with_google(
        "verified-google-token",
        request_id="login-request-id",
        on_owner_created=scheduled.append,
    )

    assert repository.created == []
    assert scheduled == []
    assert len(sessions.calls) == 1
    record = next(
        record
        for record in caplog.records
        if record.message == "owner_google_login_succeeded"
    )
    assert record.request_id == "login-request-id"
    assert record.actor_id == "owner-id"
    assert record.actor_type == ActorType.OWNER
    assert record.auth_stage == "google_login"


@pytest.mark.asyncio
async def test_google_login_rejects_password_account():
    password_owner = FakeOwner(
        password_hash="hashed-password",
        oauth_provider=None,
        oauth_subject_id=None,
    )
    service, repository, _, sessions = build_service(password_owner)

    with pytest.raises(PasswordAccountOAuthLoginError) as exc_info:
        await service.login_with_google("verified-google-token")

    assert exc_info.value.message == (
        "This email is registered with a password. "
        "Please log in using your email and password."
    )
    assert repository.created == []
    assert sessions.calls == []


@pytest.mark.asyncio
async def test_google_login_rejects_explicit_password_provider():
    password_owner = FakeOwner(
        password_hash="hashed-password",
        oauth_provider="password",
        oauth_subject_id=None,
    )
    service, _, _, sessions = build_service(password_owner)

    with pytest.raises(PasswordAccountOAuthLoginError):
        await service.login_with_google("verified-google-token")

    assert sessions.calls == []


@pytest.mark.asyncio
async def test_unverified_google_email_is_rejected_before_account_creation():
    service, repository, oauth, sessions = build_service()
    oauth.error = OAuthEmailNotVerifiedError()

    with pytest.raises(GoogleEmailNotVerifiedError):
        await service.login_with_google("verified-google-token")

    assert repository.created == []
    assert sessions.calls == []


@pytest.mark.asyncio
async def test_google_subject_mismatch_is_rejected():
    service, _, _, sessions = build_service(
        FakeOwner(oauth_subject_id="different-subject")
    )

    with pytest.raises(GoogleAccountMismatchError):
        await service.login_with_google("verified-google-token")

    assert sessions.calls == []


@pytest.mark.asyncio
async def test_invalid_google_token_is_mapped_to_safe_app_error():
    service, repository, oauth, sessions = build_service()
    oauth.error = OAuthVerificationError()

    with pytest.raises(InvalidGoogleTokenError):
        await service.login_with_google("invalid-google-token")

    assert repository.created == []
    assert sessions.calls == []


@pytest.mark.asyncio
async def test_duplicate_create_rereads_matching_google_identity(monkeypatch):
    existing = FakeOwner()

    class RacingRepository(FakeRepository):
        def __init__(self) -> None:
            super().__init__()
            self.race_completed = False

        async def get_by_email(self, email: str):
            return existing if self.race_completed else None

        async def get_by_oauth_identity(self, provider: str, provider_subject: str):
            return existing if self.race_completed else None

        async def create_google_owner(self, **kwargs):
            self.race_completed = True
            raise DuplicateKeyError("duplicate")

    repository = RacingRepository()
    sessions = FakeSessionService()
    service = OwnerOAuthAuthService(
        repository=repository,  # type: ignore[arg-type]
        oauth=FakeOAuthService(),  # type: ignore[arg-type]
        sessions=sessions,  # type: ignore[arg-type]
    )
    monkeypatch.setattr(owner_oauth_module, "create_access_token", Mock(return_value="access-token"))
    scheduled = []

    owner, _, _ = await service.login_with_google(
        "verified-google-token",
        on_owner_created=scheduled.append,
    )

    assert owner is existing
    assert len(sessions.calls) == 1
    assert scheduled == []


def test_welcome_email_failure_does_not_fail_google_signup(
    monkeypatch,
    caplog,
):
    async def login_with_google(**kwargs):
        owner = FakeOwner()
        kwargs["on_owner_created"](owner)
        return owner, "access-token", "refresh-token"

    monkeypatch.setattr(
        owner_oauth_module.owner_oauth_auth_service,
        "login_with_google",
        login_with_google,
    )
    monkeypatch.setattr(
        mailer_service,
        "send_email",
        AsyncMock(side_effect=EmailDeliveryError()),
    )
    caplog.set_level("ERROR", logger="lucidex.mailer")

    response = TestClient(app).post(
        "/api/v1/owner/auth/google",
        json={"credential": "verified-google-token"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["access_token"] == "access-token"
    assert "owner_welcome_email_failed" in caplog.text
    assert "verified-google-token" not in caplog.text


@pytest.mark.asyncio
async def test_password_login_for_google_owner_stops_before_password_and_otp(
    monkeypatch,
):
    password_verify = Mock()
    otp_create = AsyncMock()
    session_create = AsyncMock()
    monkeypatch.setattr(
        login_module.owner_repository,
        "get_by_email",
        AsyncMock(return_value=FakeOwner()),
    )
    monkeypatch.setattr(login_module, "verify_password", password_verify)
    monkeypatch.setattr(login_module.otp_service, "create_otp", otp_create)
    monkeypatch.setattr(login_module.session_service, "create_session", session_create)

    with pytest.raises(GoogleAccountPasswordLoginNotAllowedError) as exc_info:
        await LoginService().login("owner@example.com", "password")

    assert exc_info.value.message == (
        "This email is registered via Google. Please log in using Google."
    )
    password_verify.assert_not_called()
    otp_create.assert_not_awaited()
    session_create.assert_not_awaited()


def valid_google_claims(**overrides):
    claims = {
        "iss": "https://accounts.google.com",
        "aud": "google-client-id",
        "sub": "google-subject",
        "email": "Owner@Example.com",
        "email_verified": True,
        "exp": time() + 300,
        "name": "Owner Example",
        "picture": "https://example.com/avatar.png",
    }
    claims.update(overrides)
    return claims


@pytest.mark.asyncio
async def test_google_provider_normalizes_verified_identity(monkeypatch):
    verifier = Mock(return_value=valid_google_claims())
    monkeypatch.setattr(
        "src.oauth.providers.google.google_id_token.verify_oauth2_token",
        verifier,
    )

    identity = await GoogleOAuthProvider("google-client-id").verify("credential")

    assert identity.email == "owner@example.com"
    assert identity.provider_subject == "google-subject"
    verifier.assert_called_once()


@pytest.mark.asyncio
async def test_google_provider_rejects_unverified_email(monkeypatch):
    monkeypatch.setattr(
        "src.oauth.providers.google.google_id_token.verify_oauth2_token",
        Mock(return_value=valid_google_claims(email_verified=False)),
    )

    with pytest.raises(OAuthEmailNotVerifiedError):
        await GoogleOAuthProvider("google-client-id").verify("credential")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claims",
    [
        valid_google_claims(aud="wrong-client-id"),
        valid_google_claims(iss="https://untrusted.example"),
        valid_google_claims(sub=None),
        valid_google_claims(email=None),
        valid_google_claims(exp=None),
        valid_google_claims(exp=time() - 1),
    ],
)
async def test_google_provider_rejects_invalid_claims(monkeypatch, claims):
    monkeypatch.setattr(
        "src.oauth.providers.google.google_id_token.verify_oauth2_token",
        Mock(return_value=claims),
    )

    with pytest.raises(OAuthVerificationError):
        await GoogleOAuthProvider("google-client-id").verify("credential")


@pytest.mark.asyncio
@pytest.mark.parametrize("verification_error", ["bad signature", "expired"])
async def test_google_provider_hides_verification_failure(
    monkeypatch,
    verification_error,
):
    monkeypatch.setattr(
        "src.oauth.providers.google.google_id_token.verify_oauth2_token",
        Mock(side_effect=ValueError(verification_error)),
    )

    with pytest.raises(OAuthVerificationError) as exc_info:
        await GoogleOAuthProvider("google-client-id").verify("credential")

    assert verification_error not in str(exc_info.value)


def test_google_oauth_api_response_does_not_expose_credential_or_subject(
    monkeypatch,
):
    login = AsyncMock(
        return_value=(FakeOwner(), "access-token", "refresh-token")
    )
    monkeypatch.setattr(
        owner_oauth_module.owner_oauth_auth_service,
        "login_with_google",
        login,
    )

    response = TestClient(app).post(
        "/api/v1/owner/auth/google",
        json={"credential": "private-google-credential"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == {
        "access_token": "access-token",
        "token_type": "bearer",
        "refresh_token": "refresh-token",
        "owner_id": "owner-id",
        "email": "owner@example.com",
        "full_name": "Owner Example",
    }
    serialized = response.text
    assert "private-google-credential" not in serialized
    assert "google-subject" not in serialized
    assert "password_hash" not in serialized


def test_google_oauth_api_maps_invalid_token_and_is_in_openapi(
    monkeypatch,
    caplog,
):
    monkeypatch.setattr(
        owner_oauth_module.owner_oauth_auth_service,
        "login_with_google",
        AsyncMock(side_effect=InvalidGoogleTokenError()),
    )

    response = TestClient(app).post(
        "/api/v1/owner/auth/google",
        json={"credential": "invalid-google-credential"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "success": False,
        "data": None,
        "message": "Invalid or expired Google token.",
        "error_code": "INVALID_GOOGLE_TOKEN",
    }
    assert "invalid-google-credential" not in caplog.text
    error_record = next(
        record
        for record in caplog.records
        if record.name == "lucidex.exception"
        and record.message == "application_error"
    )
    assert error_record.levelname == "WARNING"
    assert error_record.status_code == 401
    assert error_record.error_code == "INVALID_GOOGLE_TOKEN"
    assert error_record.request_id
    assert "/api/v1/owner/auth/google" in app.openapi()["paths"]
    assert app.openapi()["paths"]["/api/v1/owner/auth/google"]["post"][
        "security"
    ] == []


def test_google_oauth_api_rejects_untrusted_identity_fields():
    response = TestClient(app).post(
        "/api/v1/owner/auth/google",
        json={
            "credential": "credential",
            "email": "attacker@example.com",
            "provider_subject": "attacker-subject",
        },
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("environment", ["local", "development", "test"])
def test_google_oauth_qa_page_is_available_in_safe_environments(
    monkeypatch,
    environment,
):
    monkeypatch.setattr(settings, "ENV", environment)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "qa-client-id.apps.googleusercontent.com")

    response = TestClient(app).get("/api/v1/owner/auth/google/test")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Sign in with Google" in response.text
    assert "qa-client-id.apps.googleusercontent.com" in response.text
    assert '<textarea id="token" rows="10" readonly></textarea>' in response.text
    assert "Copy Google ID token" in response.text
    assert (
        "Google ID token is temporary and sensitive. Do not share it."
        in response.text
    )
    operation = app.openapi()["paths"]["/api/v1/owner/auth/google/test"]["get"]
    assert operation["tags"] == ["Debug / Testing"]
    assert (
        "[Open Google OAuth QA page](/api/v1/owner/auth/google/test)"
        in operation["description"]
    )


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_google_oauth_qa_page_is_hidden_outside_safe_environments(
    monkeypatch,
    environment,
):
    monkeypatch.setattr(settings, "ENV", environment)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "qa-client-id.apps.googleusercontent.com")

    response = TestClient(app).get("/api/v1/owner/auth/google/test")

    assert response.status_code == 404


def test_google_oauth_qa_page_keeps_token_only_in_page_memory(
    monkeypatch,
):
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "qa-client-id.apps.googleusercontent.com")

    html = TestClient(app).get("/api/v1/owner/auth/google/test").text
    normalized_html = html.lower()

    assert (
        'document.getElementById("token").value = response.credential'
        in html
    )
    assert "navigator.clipboard.writeText(token)" in html
    assert "fetch(" not in html
    assert "console." not in html
    assert "localStorage" not in html
    assert "sessionStorage" not in html
    assert "document.cookie" not in html
    assert "client_secret" not in normalized_html
    assert "access_token" not in normalized_html
    assert "refresh_token" not in normalized_html
    assert "oauth_subject" not in normalized_html
