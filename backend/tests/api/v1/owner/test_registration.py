from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from src.mailer import mailer_service
from src.main import app
from src.owner.exceptions import PasswordMismatchError
from src.owner.models import Owner
from src.owner.services import owner_registration_service


def test_register_owner_success(monkeypatch) -> None:
    mock_owner = MagicMock(spec=Owner)
    mock_owner.id = "507f1f77bcf86cd799439011"
    mock_owner.email = "owner.test@gmail.com"
    mock_owner.status = "pending"

    register_mock = AsyncMock(return_value=mock_owner)
    monkeypatch.setattr(owner_registration_service, "register", register_mock)

    payload = {
        "email": "owner.test@gmail.com",
        "password": "VerySecurePassword123!",
        "confirm_password": "VerySecurePassword123!"
    }

    response = TestClient(app).post(
        "/api/v1/owner/register",
        json=payload,
    )

    assert response.status_code == 201
    assert response.json()["success"] is True
    assert response.json()["data"] == {
        "id": "507f1f77bcf86cd799439011",
        "email": "owner.test@gmail.com",
        "status": "pending"
    }
    register_mock.assert_awaited_once_with(
        email="owner.test@gmail.com",
        password="VerySecurePassword123!",
        confirm_password="VerySecurePassword123!"
    )


def test_register_owner_validation_error() -> None:
    # Test FastAPI/Pydantic validation: password too short, email invalid
    payload = {
        "email": "invalid-email",
        "password": "short",
        "confirm_password": "short"
    }

    response = TestClient(app).post(
        "/api/v1/owner/register",
        json=payload,
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_register_owner_service_error(monkeypatch) -> None:
    # Mock owner_registration_service to raise PasswordMismatchError
    register_mock = AsyncMock(
        side_effect=PasswordMismatchError()
    )
    monkeypatch.setattr(owner_registration_service, "register", register_mock)

    payload = {
        "email": "owner.test@gmail.com",
        "password": "Password123!",
        "confirm_password": "WrongPassword!"
    }

    response = TestClient(app).post(
        "/api/v1/owner/register",
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["success"] is False
    assert response.json()["error_code"] == "PASSWORD_MISMATCH"


def test_verify_otp_success(monkeypatch) -> None:
    mock_owner = MagicMock(spec=Owner)
    mock_owner.id = "507f1f77bcf86cd799439011"
    mock_owner.email = "owner.test@gmail.com"
    mock_owner.full_name = "Owner Test"
    mock_owner.status = "active"

    verify_mock = AsyncMock(
        return_value=(mock_owner, "access-token", "refresh-token")
    )
    welcome_mock = AsyncMock()
    monkeypatch.setattr(owner_registration_service, "verify_and_activate", verify_mock)
    monkeypatch.setattr(mailer_service, "send_welcome_email", welcome_mock)

    payload = {
        "email": "owner.test@gmail.com",
        "otp_code": "1234"
    }

    response = TestClient(app).post(
        "/api/v1/owner/verify-otp",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"] == {
        "id": "507f1f77bcf86cd799439011",
        "email": "owner.test@gmail.com",
        "status": "active",
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "token_type": "bearer",
    }
    verify_mock.assert_awaited_once_with(
        email="owner.test@gmail.com",
        otp_code="1234"
    )
    welcome_mock.assert_awaited_once_with(
        email="owner.test@gmail.com",
        owner_name="Owner Test",
    )


def test_verify_otp_invalid_code(monkeypatch) -> None:
    from src.owner.exceptions import InvalidOtpError
    verify_mock = AsyncMock(side_effect=InvalidOtpError("OTP has expired."))
    welcome_mock = AsyncMock()
    monkeypatch.setattr(owner_registration_service, "verify_and_activate", verify_mock)
    monkeypatch.setattr(mailer_service, "send_welcome_email", welcome_mock)

    payload = {
        "email": "owner.test@gmail.com",
        "otp_code": "1111"
    }

    response = TestClient(app).post(
        "/api/v1/owner/verify-otp",
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["success"] is False
    assert response.json()["error_code"] == "INVALID_OTP"
    assert "expired" in response.json()["message"]
    welcome_mock.assert_not_awaited()


def test_resend_otp_success(monkeypatch) -> None:
    resend_mock = AsyncMock()
    monkeypatch.setattr(owner_registration_service, "resend_otp", resend_mock)

    payload = {
        "email": "owner.test@gmail.com"
    }

    response = TestClient(app).post(
        "/api/v1/owner/resend-otp",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["message"] == "OTP resent successfully."
    resend_mock.assert_awaited_once_with(
        email="owner.test@gmail.com"
    )
