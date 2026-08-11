import asyncio
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from beanie import PydanticObjectId
from fastapi.testclient import TestClient

from src.auth.dependencies import require_current_actor
from src.credential.dependencies import require_current_active_owner
from src.ekyc.models import OwnerEkycIdentity
from src.ekyc.repository import EkycIdentityState, EkycRepository
from src.ekyc.schemas import VerifyOwnerEkycData
from src.ekyc.services import EkycVerificationService, ekyc_verification_service
from src.ekyc.services import verification as ekyc_verification_module
from src.exceptions import AppError
from src.main import app
from src.organization.models import InstitutionAccount
from src.owner.constants import OwnerStatus
from src.owner.models import Owner
from src.owner.repository import OwnerRepository
from src.utils.hashing import hash_national_id

OWNER_ID = PydanticObjectId("507f1f77bcf86cd799439011")
NOW = datetime(2026, 7, 29, 9, 30, tzinfo=UTC)
SECRET = "ekyc-test-secret"
NATIONAL_ID = "079203001234"


def make_owner(
    *,
    status: OwnerStatus = OwnerStatus.ACTIVE,
    deleted_at: datetime | None = None,
) -> Owner:
    return Owner.model_construct(
        id=OWNER_ID,
        email="owner@example.com",
        status=status,
        deleted_at=deleted_at,
    )


class OwnerStateRepository:
    def __init__(
        self,
        *,
        legacy_hash: str | None = None,
        clear_succeeds: bool = True,
    ) -> None:
        self.legacy_hash = legacy_hash
        self.clear_succeeds = clear_succeeds
        self.cleared_owner_id: PydanticObjectId | None = None

    async def get_legacy_national_id_hash(
        self,
        _owner_id: PydanticObjectId,
    ) -> str | None:
        return self.legacy_hash

    async def clear_legacy_ekyc_fields(
        self,
        owner_id: PydanticObjectId,
    ) -> bool:
        self.cleared_owner_id = owner_id
        return self.clear_succeeds


class IdentityRepository:
    def __init__(
        self,
        *,
        persisted: bool = True,
        existing_owner: EkycIdentityState | None = None,
        existing_hash: EkycIdentityState | None = None,
    ) -> None:
        self.persisted = persisted
        self.existing_owner = existing_owner
        self.existing_hash = existing_hash
        self.arguments: dict[str, Any] | None = None

    async def bind_verified_identity(
        self,
        **kwargs: Any,
    ) -> EkycIdentityState | None:
        self.arguments = kwargs
        if not self.persisted:
            return None
        return EkycIdentityState(
            owner_id=kwargs["owner_id"],
            national_id_hash=kwargs["national_id_hash"],
            status="verified",
            verified_at=NOW,
        )

    async def get_verified_identity(
        self,
        _owner_id: PydanticObjectId,
    ) -> EkycIdentityState | None:
        return self.existing_owner

    async def get_by_national_id_hash(
        self,
        _national_id_hash: str,
    ) -> EkycIdentityState | None:
        return self.existing_hash


def make_service(
    owners: OwnerStateRepository,
    identities: IdentityRepository | None = None,
) -> EkycVerificationService:
    return EkycVerificationService(
        cast(OwnerRepository, owners),
        cast(EkycRepository, identities or IdentityRepository()),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "national_id",
    [
        "",
        "07920300123",
        "0792030012345",
        "07920300123A",
        "07920300123_",
        "079.203.001234",
    ],
)
async def test_invalid_national_id_format_is_rejected(national_id: str) -> None:
    service = make_service(OwnerStateRepository())

    with pytest.raises(AppError) as exc_info:
        await service.verify_owner_national_id(
            owner=make_owner(),
            national_id=national_id,
            secret=SECRET,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.error_code == "INVALID_NATIONAL_ID_FORMAT"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "national_id",
    [
        NATIONAL_ID,
        " 079 203 001234 ",
        "079-203-001234",
    ],
)
async def test_valid_normalized_national_id_persists_only_hash(
    national_id: str,
) -> None:
    expected_hash = hash_national_id(NATIONAL_ID, SECRET)
    owners = OwnerStateRepository()
    identities = IdentityRepository()
    service = make_service(owners, identities)

    result = await service.verify_owner_national_id(
        owner=make_owner(),
        national_id=national_id,
        secret=SECRET,
    )

    assert result == VerifyOwnerEkycData(
        identity_matched=True,
        ekyc_status="verified",
        verified_at=NOW,
    )
    assert owners.cleared_owner_id == OWNER_ID
    assert identities.arguments is not None
    assert identities.arguments["owner_id"] == OWNER_ID
    assert identities.arguments["national_id_hash"] == expected_hash
    assert isinstance(identities.arguments["verified_at"], datetime)


@pytest.mark.asyncio
async def test_ekyc_does_not_log_plaintext_or_full_hash(caplog) -> None:
    generated_hash = hash_national_id(NATIONAL_ID, SECRET)
    owners = OwnerStateRepository()

    await make_service(owners).verify_owner_national_id(
        owner=make_owner(),
        national_id=NATIONAL_ID,
        secret=SECRET,
    )

    assert NATIONAL_ID not in caplog.text
    assert generated_hash not in caplog.text


@pytest.mark.asyncio
async def test_same_hash_is_idempotent() -> None:
    existing_hash = hash_national_id(NATIONAL_ID, SECRET)
    owners = OwnerStateRepository()
    identities = IdentityRepository()
    service = make_service(owners, identities)

    result = await service.verify_owner_national_id(
        owner=make_owner(),
        national_id=NATIONAL_ID,
        secret=SECRET,
    )

    assert result.verified_at == NOW
    assert owners.cleared_owner_id == OWNER_ID
    assert identities.arguments is not None
    assert identities.arguments["national_id_hash"] == existing_hash


@pytest.mark.asyncio
async def test_ekyc_identity_persistence_failure_is_reported() -> None:
    owners = OwnerStateRepository()

    with pytest.raises(AppError) as exc_info:
        await make_service(
            owners,
            IdentityRepository(persisted=False),
        ).verify_owner_national_id(
            owner=make_owner(),
            national_id=NATIONAL_ID,
            secret=SECRET,
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.error_code == "EKYC_PERSISTENCE_FAILED"


@pytest.mark.asyncio
async def test_different_existing_hash_is_not_overwritten() -> None:
    owners = OwnerStateRepository()
    service = make_service(
        owners,
        IdentityRepository(
            persisted=False,
            existing_owner=EkycIdentityState(
                owner_id=OWNER_ID,
                national_id_hash="b" * 64,
                status="verified",
                verified_at=NOW,
            ),
        ),
    )

    with pytest.raises(AppError) as exc_info:
        await service.verify_owner_national_id(
            owner=make_owner(),
            national_id=NATIONAL_ID,
            secret=SECRET,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == "IDENTITY_CHANGE_NOT_ALLOWED"
    assert owners.cleared_owner_id is None


@pytest.mark.asyncio
async def test_legacy_owner_hash_cannot_be_replaced_during_migration() -> None:
    owners = OwnerStateRepository(legacy_hash="b" * 64)
    identities = IdentityRepository()

    with pytest.raises(AppError) as exc_info:
        await make_service(owners, identities).verify_owner_national_id(
            owner=make_owner(),
            national_id=NATIONAL_ID,
            secret=SECRET,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == "IDENTITY_CHANGE_NOT_ALLOWED"
    assert identities.arguments is None
    assert owners.cleared_owner_id is None


@pytest.mark.asyncio
async def test_national_id_linked_to_another_owner_is_rejected() -> None:
    generated_hash = hash_national_id(NATIONAL_ID, SECRET)
    identities = IdentityRepository(
        persisted=False,
        existing_hash=EkycIdentityState(
            owner_id=PydanticObjectId("507f1f77bcf86cd799439012"),
            national_id_hash=generated_hash,
            status="verified",
            verified_at=NOW,
        ),
    )

    with pytest.raises(AppError) as exc_info:
        await make_service(
            OwnerStateRepository(),
            identities,
        ).verify_owner_national_id(
            owner=make_owner(),
            national_id=NATIONAL_ID,
            secret=SECRET,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "IDENTITY_ALREADY_LINKED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "owner",
    [
        make_owner(status=OwnerStatus.PENDING),
        make_owner(status=OwnerStatus.LOCKED_MIGRATED),
        make_owner(status=OwnerStatus.SOFT_DELETED),
        make_owner(deleted_at=NOW),
    ],
)
async def test_inactive_locked_or_deleted_owner_is_rejected(owner: Owner) -> None:
    owners = OwnerStateRepository()

    with pytest.raises(AppError) as exc_info:
        await make_service(owners).verify_owner_national_id(
            owner=owner,
            national_id=NATIONAL_ID,
            secret=SECRET,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == "OWNER_INACTIVE"
    assert owners.cleared_owner_id is None


@pytest.mark.asyncio
async def test_legacy_owner_field_cleanup_failure_is_reported() -> None:
    owners = OwnerStateRepository(clear_succeeds=False)

    with pytest.raises(AppError) as exc_info:
        await make_service(owners).verify_owner_national_id(
            owner=make_owner(),
            national_id=NATIONAL_ID,
            secret=SECRET,
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.error_code == "EKYC_PERSISTENCE_FAILED"


class RacingOwnerRepository:
    async def get_legacy_national_id_hash(
        self,
        _owner_id: PydanticObjectId,
    ) -> str | None:
        return None

    async def clear_legacy_ekyc_fields(
        self,
        owner_id: PydanticObjectId,
    ) -> bool:
        assert owner_id == OWNER_ID
        return True


class RacingIdentityRepository:
    def __init__(self) -> None:
        self.state: EkycIdentityState | None = None
        self.lock = asyncio.Lock()

    async def bind_verified_identity(
        self,
        **kwargs: Any,
    ) -> EkycIdentityState | None:
        async with self.lock:
            if self.state is None:
                self.state = EkycIdentityState(
                    owner_id=kwargs["owner_id"],
                    national_id_hash=kwargs["national_id_hash"],
                    status="verified",
                    verified_at=NOW,
                )
                return self.state
            if self.state.national_id_hash == kwargs["national_id_hash"]:
                return self.state
            return None

    async def get_verified_identity(
        self,
        _owner_id: PydanticObjectId,
    ) -> EkycIdentityState | None:
        return self.state

    async def get_by_national_id_hash(
        self,
        national_id_hash: str,
    ) -> EkycIdentityState | None:
        if self.state and self.state.national_id_hash == national_id_hash:
            return self.state
        return None


@pytest.mark.asyncio
async def test_two_different_hashes_race_only_persists_one() -> None:
    owners = RacingOwnerRepository()
    identities = RacingIdentityRepository()
    service = EkycVerificationService(
        cast(OwnerRepository, owners),
        cast(EkycRepository, identities),
    )

    results = await asyncio.gather(
        service.verify_owner_national_id(
            owner=make_owner(),
            national_id=NATIONAL_ID,
            secret=SECRET,
        ),
        service.verify_owner_national_id(
            owner=make_owner(),
            national_id="001204000001",
            secret=SECRET,
        ),
        return_exceptions=True,
    )

    assert sum(isinstance(result, VerifyOwnerEkycData) for result in results) == 1
    conflicts = [result for result in results if isinstance(result, AppError)]
    assert len(conflicts) == 1
    assert conflicts[0].status_code == 403
    assert conflicts[0].error_code == "IDENTITY_CHANGE_NOT_ALLOWED"
    assert identities.state is not None


class RecordingOwnerCollection:
    def __init__(self) -> None:
        self.query: dict[str, Any] | None = None
        self.update: dict[str, Any] | None = None
    async def update_one(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
    ) -> Any:
        self.query = query
        self.update = update
        return type("UpdateResult", (), {"matched_count": 1})()


class RecordingEkycCollection:
    def __init__(self) -> None:
        self.query: dict[str, Any] | None = None
        self.update: dict[str, Any] | None = None
        self.upsert: bool | None = None
        self.options: dict[str, Any] | None = None

    async def find_one_and_update(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
        **options: Any,
    ) -> dict[str, Any]:
        self.query = query
        self.update = update
        self.upsert = options["upsert"]
        self.options = options
        return {
            "owner_id": OWNER_ID,
            "national_id_hash": update["$set"]["national_id_hash"],
            "status": "verified",
            "verified_at": update["$setOnInsert"]["verified_at"],
        }


@pytest.mark.asyncio
async def test_ekyc_repository_binds_verified_owner_identity(monkeypatch) -> None:
    collection = RecordingEkycCollection()
    monkeypatch.setattr(
        OwnerEkycIdentity,
        "get_motor_collection",
        classmethod(lambda cls: collection),
    )
    generated_hash = hash_national_id(NATIONAL_ID, SECRET)

    persisted = await EkycRepository().bind_verified_identity(
        owner_id=OWNER_ID,
        national_id_hash=generated_hash,
        verified_at=NOW,
    )

    assert persisted is not None
    assert persisted.national_id_hash == generated_hash
    assert collection.query == {
        "owner_id": OWNER_ID,
        "$or": [
            {"national_id_hash": generated_hash},
            {"national_id_hash": None},
            {"national_id_hash": {"$exists": False}},
        ],
    }
    assert collection.update == {
        "$set": {
            "national_id_hash": generated_hash,
            "status": "verified",
        },
        "$setOnInsert": {
            "owner_id": OWNER_ID,
            "verified_at": NOW,
        },
    }
    assert collection.upsert is True


@pytest.mark.asyncio
async def test_owner_repository_clears_legacy_ekyc_fields(monkeypatch) -> None:
    collection = RecordingOwnerCollection()
    monkeypatch.setattr(
        Owner,
        "get_motor_collection",
        classmethod(lambda cls: collection),
    )
    cleared = await OwnerRepository().clear_legacy_ekyc_fields(OWNER_ID)

    assert cleared is True
    assert collection.query == {
        "_id": OWNER_ID,
        "status": OwnerStatus.ACTIVE.value,
        "deleted_at": None,
    }
    assert collection.update == {
        "$unset": {
            "ekyc_verified": "",
            "ekyc_verified_at": "",
            "verified_national_id_hash": "",
        }
    }


def test_verify_ekyc_http_happy_path_and_safe_response(monkeypatch) -> None:
    generated_hash = hash_national_id(NATIONAL_ID, SECRET)
    identities = IdentityRepository()
    owners = OwnerStateRepository()
    monkeypatch.setattr(
        ekyc_verification_service,
        "_owners",
        owners,
    )
    monkeypatch.setattr(
        ekyc_verification_service,
        "_repository",
        identities,
    )
    monkeypatch.setattr(
        ekyc_verification_module,
        "get_national_id_hash_secret",
        lambda: SECRET,
    )
    app.dependency_overrides[require_current_active_owner] = make_owner
    try:
        response = TestClient(app).post(
            "/api/v1/owner/ekyc/verify",
            json={"national_id": NATIONAL_ID},
        )
    finally:
        app.dependency_overrides.pop(require_current_active_owner, None)

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {
            "identity_matched": True,
            "ekyc_status": "verified",
            "verified_at": "2026-07-29T09:30:00Z",
        },
        "message": "Identity verified successfully.",
        "error_code": None,
    }
    assert NATIONAL_ID not in response.text
    assert "national_id_hash" not in response.text
    assert owners.cleared_owner_id == OWNER_ID
    assert identities.arguments is not None
    assert identities.arguments["owner_id"] == OWNER_ID
    assert identities.arguments["national_id_hash"] == generated_hash


@pytest.mark.parametrize(
    ("body", "expected_error_code"),
    [
        ({}, "VALIDATION_ERROR"),
        ({"national_id": None}, "VALIDATION_ERROR"),
        ({"national_id": ""}, "VALIDATION_ERROR"),
        ({"national_id": 79203001234}, "VALIDATION_ERROR"),
        ({"national_id": "07920300123A"}, "INVALID_NATIONAL_ID_FORMAT"),
        ({"national_id": "07920300123"}, "INVALID_NATIONAL_ID_FORMAT"),
        ({"national_id": "0792030012345"}, "INVALID_NATIONAL_ID_FORMAT"),
        ({"national_id": "07920300123_"}, "INVALID_NATIONAL_ID_FORMAT"),
        (
            {"national_id": NATIONAL_ID, "owner_id": str(OWNER_ID)},
            "VALIDATION_ERROR",
        ),
    ],
)
def test_verify_ekyc_request_schema_rejects_invalid_body(
    body: dict[str, Any],
    expected_error_code: str,
) -> None:
    app.dependency_overrides[require_current_active_owner] = make_owner
    try:
        response = TestClient(app).post(
            "/api/v1/owner/ekyc/verify",
            json=body,
        )
    finally:
        app.dependency_overrides.pop(require_current_active_owner, None)

    assert response.status_code == 422
    assert response.json()["error_code"] == expected_error_code


def test_verify_ekyc_requires_authentication() -> None:
    response = TestClient(app).post(
        "/api/v1/owner/ekyc/verify",
        json={"national_id": NATIONAL_ID},
    )

    assert response.status_code == 401
    assert response.json()["error_code"] == "UNAUTHORIZED"


def test_verify_ekyc_rejects_non_owner_actor() -> None:
    actor = InstitutionAccount.model_construct(
        id=PydanticObjectId("507f1f77bcf86cd799439012"),
        email="institution@example.com",
        status="active",
    )
    app.dependency_overrides[require_current_actor] = lambda: (
        actor,
        object(),
        "institution_account",
    )
    try:
        response = TestClient(app).post(
            "/api/v1/owner/ekyc/verify",
            json={"national_id": NATIONAL_ID},
        )
    finally:
        app.dependency_overrides.pop(require_current_actor, None)

    assert response.status_code == 403
    assert response.json()["error_code"] == "OWNER_ACCESS_REQUIRED"


@pytest.mark.parametrize(
    "owner",
    [
        make_owner(status=OwnerStatus.PENDING),
        make_owner(status=OwnerStatus.LOCKED_MIGRATED),
        make_owner(status=OwnerStatus.SOFT_DELETED),
        make_owner(deleted_at=NOW),
    ],
)
def test_verify_ekyc_http_lifecycle_is_denied(owner: Owner) -> None:
    app.dependency_overrides[require_current_actor] = lambda: (
        owner,
        object(),
        "owner",
    )
    try:
        response = TestClient(app).post(
            "/api/v1/owner/ekyc/verify",
            json={"national_id": NATIONAL_ID},
        )
    finally:
        app.dependency_overrides.pop(require_current_actor, None)

    assert response.status_code == 403


def test_verify_ekyc_openapi_contract() -> None:
    schema = app.openapi()
    operation = schema["paths"]["/api/v1/owner/ekyc/verify"]["post"]

    assert set(operation["responses"]) == {
        "200",
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    }
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    assert request_schema["$ref"].endswith("/VerifyOwnerEkycRequest")
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert "ApiResponse_VerifyOwnerEkycData_" in response_schema["$ref"]
    assert schema["security"] == [{"BearerAuth": []}]
    assert list(schema["paths"]).count("/api/v1/owner/ekyc/verify") == 1
