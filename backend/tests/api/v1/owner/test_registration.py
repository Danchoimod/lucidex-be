from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.owner.service import owner_registration_service
from src.owner.exceptions import PasswordMismatchError
from src.owner.models import Owner


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
