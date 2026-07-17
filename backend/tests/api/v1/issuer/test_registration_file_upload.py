from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.main import app
from src.organization.models import OrganizationStatus
from src.organization.services.registration import issuer_registration_service


def test_register_issuer_accepts_pdf_upload(monkeypatch) -> None:
    register = AsyncMock(
        return_value=SimpleNamespace(
            id="507f1f77bcf86cd799439013",
            status=OrganizationStatus.PENDING_REVIEW,
        )
    )
    monkeypatch.setattr(issuer_registration_service, "register", register)

    response = TestClient(app).post(
        "/api/v1/issuer/register",
        data={
            "name": "Upload Test Company",
            "tax_code": "0312345684",
            "address": "District 1",
            "legal_rep_name": "Test Rep",
            "contact_email": "issuer.test@gmail.com",
            "contact_phone": "0912345678",
            "registrant_name": "Test User",
        },
        files={"document": ("sample.pdf", b"%PDF-1.4\n%test", "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["data"]["status"] == "pending_review"
    register.assert_awaited_once()
