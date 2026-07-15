from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.v1.issuer.router import issuer_registration_service
from app.main import app
from app.models.enums import OrganizationStatus
from app.services.registration_service import TaxCodeAlreadyRegisteredError


def _valid_payload() -> dict[str, str]:
    return {
        "name": "Example University",
        "tax_code": "0312345678",
        "address": "Ho Chi Minh City",
        "legal_rep_name": "Nguyen Van A",
        "contact_email": "issuer.test@gmail.com",
        "contact_phone": "0912345678",
        "registrant_name": "Tran Van B",
    }


def test_register_issuer_success(monkeypatch) -> None:
    register = AsyncMock(
        return_value=SimpleNamespace(
            id="507f1f77bcf86cd799439011",
            status=OrganizationStatus.PENDING_REVIEW,
        )
    )
    monkeypatch.setattr(issuer_registration_service, "register", register)

    response = TestClient(app).post(
        "/api/v1/issuer/register",
        json=_valid_payload(),
    )

    assert response.status_code == 201
    assert response.json()["data"] == {
        "id": "507f1f77bcf86cd799439011",
        "status": "pending_review",
    }
    register.assert_awaited_once()


def test_register_issuer_returns_field_validation_errors() -> None:
    payload = _valid_payload()
    payload.update(
        tax_code="invalid",
        contact_email="issuer@example.com",
        contact_phone="123",
    )

    response = TestClient(app).post(
        "/api/v1/issuer/register",
        json=payload,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert {error["field"] for error in body["data"]["errors"]} == {
        "tax_code",
        "contact_email",
        "contact_phone",
    }


def test_register_issuer_returns_tax_code_conflict(monkeypatch) -> None:
    register = AsyncMock(side_effect=TaxCodeAlreadyRegisteredError())
    monkeypatch.setattr(issuer_registration_service, "register", register)

    response = TestClient(app).post(
        "/api/v1/issuer/register",
        json=_valid_payload(),
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "TAX_CODE_ALREADY_REGISTERED"
