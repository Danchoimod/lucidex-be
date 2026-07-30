import hashlib
import hmac
import re
from datetime import datetime
from typing import Any, cast

import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from src.config import Settings
from src.credential import config as credential_config
from src.credential.exceptions import NationalIdHashSecretNotConfiguredError
from src.credential.services import hashing as credential_hashing
from src.ekyc.repository import EkycIdentityState, EkycRepository
from src.ekyc.services import EkycVerificationService
from src.ekyc.services import verification as ekyc_verification
from src.exceptions import AppError
from src.owner.constants import OwnerStatus
from src.owner.models import Owner
from src.owner.repository import OwnerRepository
from src.utils import hashing
from src.utils.hashing import hash_national_id, normalize_national_id


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("079203001234", "079203001234"),
        (" 079 203 001234 ", "079203001234"),
        ("079-203-001234", "079203001234"),
    ],
)
def test_normalize_national_id(value: str, expected: str) -> None:
    assert normalize_national_id(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "07920300123A",
        "07920300123",
        "0792030012345",
    ],
)
def test_normalize_national_id_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_national_id(value)


def test_hash_national_id_uses_deterministic_hmac_sha256() -> None:
    national_id = "079-203-001234"
    secret = "test-national-id-secret"
    expected = hmac.new(
        secret.encode(),
        b"079203001234",
        hashlib.sha256,
    ).hexdigest()

    first = hash_national_id(national_id, secret)
    second = hash_national_id("079 203 001234", secret)

    assert first == expected
    assert second == expected
    assert first != hashlib.sha256(b"079203001234").hexdigest()
    assert re.fullmatch(r"[0-9a-f]{64}", first)


def test_hash_national_id_changes_with_secret() -> None:
    first = hash_national_id("079203001234", "first-secret")
    second = hash_national_id("079203001234", "second-secret")

    assert first != second


def test_production_requires_dedicated_hash_secret(monkeypatch) -> None:
    monkeypatch.delenv("NATIONAL_ID_HASH_SECRET", raising=False)
    settings_data = {
        "ENV": "production",
        "MONGODB_URI": "mongodb://localhost:27017",
        "JWT_SECRET_KEY": "j" * 32,
        "_env_file": None,
    }

    with pytest.raises(ValidationError):
        Settings(**settings_data)

    configured = Settings(
        **settings_data,
        NATIONAL_ID_HASH_SECRET="dedicated-national-id-secret",
    )
    assert configured.NATIONAL_ID_HASH_SECRET == "dedicated-national-id-secret"


def test_non_production_can_start_without_hash_secret(monkeypatch) -> None:
    monkeypatch.delenv("NATIONAL_ID_HASH_SECRET", raising=False)

    configured = Settings(
        ENV="development",
        MONGODB_URI="mongodb://localhost:27017",
        JWT_SECRET_KEY="j" * 32,
        _env_file=None,
    )

    assert configured.NATIONAL_ID_HASH_SECRET is None


def test_hash_operation_uses_defined_error_when_secret_is_missing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        credential_config.settings,
        "NATIONAL_ID_HASH_SECRET",
        None,
    )

    with pytest.raises(NationalIdHashSecretNotConfiguredError) as exc_info:
        credential_config.get_national_id_hash_secret()

    assert exc_info.value.status_code == 500
    assert exc_info.value.error_code == "NATIONAL_ID_HASH_SECRET_NOT_CONFIGURED"


def test_import_and_ekyc_use_the_shared_hash_helper() -> None:
    assert credential_hashing.hash_national_id is hashing.hash_national_id
    assert ekyc_verification.hash_national_id is hashing.hash_national_id
    assert credential_hashing.hash_imported_national_id(
        "079 203 001234",
        secret="shared-secret",
    ) == hashing.hash_national_id("079203001234", "shared-secret")


class RecordingOwnerRepository:
    def __init__(self, owner: Owner) -> None:
        self.owner = owner
        self.cleared_owner_id: PydanticObjectId | None = None

    async def get_legacy_national_id_hash(
        self,
        _owner_id: PydanticObjectId,
    ) -> str | None:
        return None

    async def clear_legacy_ekyc_fields(
        self,
        owner_id: PydanticObjectId,
    ) -> bool:
        self.cleared_owner_id = owner_id
        return True


class RecordingEkycRepository:
    def __init__(
        self,
        *,
        existing_hash: str | None = None,
        verified_at: datetime | None = None,
    ) -> None:
        self.existing_hash = existing_hash
        self.verified_at = verified_at
        self.arguments: dict[str, Any] | None = None

    async def bind_verified_identity(
        self,
        **kwargs: Any,
    ) -> EkycIdentityState | None:
        self.arguments = kwargs
        if self.existing_hash and self.existing_hash != kwargs["national_id_hash"]:
            return None
        return EkycIdentityState(
            owner_id=kwargs["owner_id"],
            national_id_hash=kwargs["national_id_hash"],
            status="verified",
            verified_at=self.verified_at or kwargs["verified_at"],
        )

    async def get_verified_identity(
        self,
        owner_id: PydanticObjectId,
    ) -> EkycIdentityState | None:
        if not self.existing_hash:
            return None
        return EkycIdentityState(
            owner_id=owner_id,
            national_id_hash=self.existing_hash,
            status="verified",
            verified_at=self.verified_at or datetime(2026, 7, 29),
        )

    async def get_by_national_id_hash(
        self,
        _national_id_hash: str,
    ) -> EkycIdentityState | None:
        return None


def make_ekyc_service(
    owner_repository: RecordingOwnerRepository,
    identity_repository: RecordingEkycRepository | None = None,
) -> EkycVerificationService:
    return EkycVerificationService(
        cast(OwnerRepository, owner_repository),
        cast(
            EkycRepository,
            identity_repository or RecordingEkycRepository(),
        ),
    )


@pytest.mark.asyncio
async def test_ekyc_persists_only_the_canonical_hash() -> None:
    owner = Owner.model_construct(
        id=PydanticObjectId("507f1f77bcf86cd799439011"),
        email="owner@example.com",
        status=OwnerStatus.ACTIVE,
    )
    owner_repository = RecordingOwnerRepository(owner)
    identity_repository = RecordingEkycRepository()
    service = make_ekyc_service(owner_repository, identity_repository)

    result = await service.verify_owner_national_id(
        owner=owner,
        national_id="079-203-001234",
        secret="ekyc-test-secret",
    )

    assert result.identity_matched is True
    assert result.ekyc_status == "verified"
    assert isinstance(result.verified_at, datetime)
    assert owner_repository.cleared_owner_id == owner.id
    assert identity_repository.arguments is not None
    assert identity_repository.arguments["national_id_hash"] == hash_national_id(
        "079203001234",
        "ekyc-test-secret",
    )
    assert "national_id" not in identity_repository.arguments


@pytest.mark.asyncio
async def test_ekyc_same_hash_is_idempotent() -> None:
    existing_hash = hash_national_id("079203001234", "ekyc-test-secret")
    existing_verified_at = datetime(2026, 7, 29)
    owner = Owner.model_construct(
        id=PydanticObjectId("507f1f77bcf86cd799439011"),
        email="owner@example.com",
        status=OwnerStatus.ACTIVE,
    )
    owner_repository = RecordingOwnerRepository(owner)
    service = make_ekyc_service(
        owner_repository,
        RecordingEkycRepository(
            existing_hash=existing_hash,
            verified_at=existing_verified_at,
        ),
    )

    result = await service.verify_owner_national_id(
        owner=owner,
        national_id="079-203-001234",
        secret="ekyc-test-secret",
    )

    assert result.identity_matched is True
    assert result.verified_at == existing_verified_at
    assert owner_repository.cleared_owner_id == owner.id


@pytest.mark.asyncio
async def test_ekyc_rejects_identity_overwrite() -> None:
    owner = Owner.model_construct(
        id=PydanticObjectId("507f1f77bcf86cd799439011"),
        email="owner@example.com",
        status=OwnerStatus.ACTIVE,
    )
    owner_repository = RecordingOwnerRepository(owner)
    service = make_ekyc_service(
        owner_repository,
        RecordingEkycRepository(existing_hash="b" * 64),
    )

    with pytest.raises(AppError) as exc_info:
        await service.verify_owner_national_id(
            owner=owner,
            national_id="079203001234",
            secret="ekyc-test-secret",
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == "IDENTITY_CHANGE_NOT_ALLOWED"
    assert owner_repository.cleared_owner_id is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "owner",
    [
        Owner.model_construct(
            id=PydanticObjectId("507f1f77bcf86cd799439011"),
            email="owner@example.com",
            status=OwnerStatus.PENDING,
        ),
        Owner.model_construct(
            id=PydanticObjectId("507f1f77bcf86cd799439011"),
            email="owner@example.com",
            status=OwnerStatus.ACTIVE,
            deleted_at=datetime(2026, 7, 30),
        ),
    ],
)
async def test_ekyc_rejects_inactive_or_deleted_owner(owner: Owner) -> None:
    owner_repository = RecordingOwnerRepository(owner)
    service = make_ekyc_service(owner_repository)

    with pytest.raises(AppError) as exc_info:
        await service.verify_owner_national_id(
            owner=owner,
            national_id="079203001234",
            secret="ekyc-test-secret",
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == "OWNER_INACTIVE"
    assert owner_repository.cleared_owner_id is None
