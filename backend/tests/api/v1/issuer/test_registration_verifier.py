from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.main import app
from src.organization.constants import OrganizationType
from src.organization.models import OrganizationStatus
from src.organization.services.registration import issuer_registration_service


def test_register_verifier_uses_verifier_mail_template(monkeypatch) -> None:
    register = AsyncMock(
        return_value=SimpleNamespace(
            id="507f1f77bcf86cd799439012",
            status=OrganizationStatus.PENDING_REVIEW,
            type=OrganizationType.VERIFIER,
        )
    )
    monkeypatch.setattr(issuer_registration_service, "register", register)

    response = TestClient(app).post(
        "/api/v1/issuer/register",
        json={
            "name": "University Test",
            "tax_code": "0312345680",
            "address": "Hanoi",
            "legal_rep_name": "Test Person",
            "contact_email": "issuer.test@gmail.com",
            "contact_phone": "0912345678",
            "registrant_name": "Jane Doe",
        },
    )

    assert response.status_code == 201
    assert response.json()["data"]["status"] == "pending_review"
    register.assert_awaited_once()
