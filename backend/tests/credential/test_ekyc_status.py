from datetime import UTC, datetime
from typing import cast

import pytest
from beanie import PydanticObjectId
from fastapi.testclient import TestClient

from src.credential.dependencies import require_current_active_owner
from src.ekyc.repository import EkycIdentityState, EkycRepository
from src.ekyc.services import OwnerEkycStatusService, owner_ekyc_status_service
from src.exceptions import AppError
from src.main import app
from src.owner.constants import OwnerStatus
from src.owner.models import Owner

OWNER_ID = PydanticObjectId("507f1f77bcf86cd799439011")
VERIFICATION_ID = PydanticObjectId("507f1f77bcf86cd799439015")
NOW = datetime(2026, 7, 28, 9, 30, tzinfo=UTC)


def make_owner() -> Owner:
    return Owner.model_construct(
        id=OWNER_ID,
        email="owner@example.com",
        status=OwnerStatus.ACTIVE,
        deleted_at=None,
    )


class StatusRepository:
    def __init__(self, identity: EkycIdentityState | None) -> None:
        self.identity = identity
        self.owner_id: PydanticObjectId | None = None

    async def get_verified_identity(
        self,
        owner_id: PydanticObjectId,
    ) -> EkycIdentityState | None:
        self.owner_id = owner_id
        return self.identity


def make_service(
    identity: EkycIdentityState | None,
) -> tuple[OwnerEkycStatusService, StatusRepository]:
    repository = StatusRepository(identity)
    return (
        OwnerEkycStatusService(cast(EkycRepository, repository)),
        repository,
    )


@pytest.mark.asyncio
async def test_status_returns_not_verified_without_identity() -> None:
    service, repository = make_service(None)

    result = await service.get_status(owner=make_owner())

    assert result.model_dump() == {
        "status": "not_verified",
        "verification_id": None,
        "provider": None,
        "verified_at": None,
    }
    assert repository.owner_id == OWNER_ID


@pytest.mark.asyncio
async def test_status_returns_persisted_verified_identity() -> None:
    service, repository = make_service(
        EkycIdentityState(
            owner_id=OWNER_ID,
            national_id_hash="a" * 64,
            status="verified",
            verified_at=NOW,
            verification_id=VERIFICATION_ID,
            provider="vnpt",
        )
    )

    result = await service.get_status(owner=make_owner())

    assert result.model_dump() == {
        "status": "verified",
        "verification_id": str(VERIFICATION_ID),
        "provider": "vnpt",
        "verified_at": NOW,
    }
    assert repository.owner_id == OWNER_ID


@pytest.mark.asyncio
async def test_status_reports_owner_without_id_as_not_found() -> None:
    service, _ = make_service(None)
    owner = Owner.model_construct(
        id=None,
        email="owner@example.com",
        status=OwnerStatus.ACTIVE,
    )

    with pytest.raises(AppError) as exc_info:
        await service.get_status(owner=owner)

    assert exc_info.value.status_code == 404
    assert exc_info.value.error_code == "OWNER_NOT_FOUND"


def test_status_http_verified_response(monkeypatch) -> None:
    service, _ = make_service(
        EkycIdentityState(
            owner_id=OWNER_ID,
            national_id_hash="a" * 64,
            status="verified",
            verified_at=NOW,
            verification_id=VERIFICATION_ID,
            provider="vnpt",
        )
    )
    monkeypatch.setattr(
        owner_ekyc_status_service,
        "_repository",
        service._repository,
    )
    app.dependency_overrides[require_current_active_owner] = make_owner
    try:
        response = TestClient(app).get("/api/v1/owner/ekyc/status")
    finally:
        app.dependency_overrides.pop(require_current_active_owner, None)

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {
            "status": "verified",
            "verification_id": str(VERIFICATION_ID),
            "provider": "vnpt",
            "verified_at": "2026-07-28T09:30:00Z",
        },
        "message": "Owner eKYC status retrieved successfully.",
        "error_code": None,
    }


def test_status_http_not_verified_response(monkeypatch) -> None:
    service, _ = make_service(None)
    monkeypatch.setattr(
        owner_ekyc_status_service,
        "_repository",
        service._repository,
    )
    app.dependency_overrides[require_current_active_owner] = make_owner
    try:
        response = TestClient(app).get("/api/v1/owner/ekyc/status")
    finally:
        app.dependency_overrides.pop(require_current_active_owner, None)

    assert response.status_code == 200
    assert response.json()["data"] == {
        "status": "not_verified",
        "verification_id": None,
        "provider": None,
        "verified_at": None,
    }


def test_status_requires_authentication() -> None:
    response = TestClient(app).get("/api/v1/owner/ekyc/status")

    assert response.status_code == 401
    assert response.json()["error_code"] == "UNAUTHORIZED"


def test_status_openapi_contract() -> None:
    operation = app.openapi()["paths"]["/api/v1/owner/ekyc/status"]["get"]

    assert set(operation["responses"]) == {"200", "401", "403", "404", "500"}
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert "ApiResponse_OwnerEkycStatusData_" in response_schema["$ref"]
