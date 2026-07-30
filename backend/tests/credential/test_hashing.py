import hashlib
import hmac
import re
from datetime import datetime
from typing import Any, cast

import pytest
from beanie import PydanticObjectId
from fastapi import HTTPException
from pydantic import ValidationError

from src.config import Settings
from src.credential import service as credential_service
from src.ekyc import service as ekyc_service
from src.ekyc.repository import EkycRepository
from src.ekyc.service import EkycVerificationService
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


def test_import_and_ekyc_use_the_shared_hash_helper() -> None:
    assert credential_service.hash_national_id is hashing.hash_national_id
    assert ekyc_service.hash_national_id is hashing.hash_national_id
    assert credential_service.hash_imported_national_id(
        "079 203 001234",
        secret="shared-secret",
    ) == hashing.hash_national_id("079203001234", "shared-secret")


class MatchingEkycRepository:
    def __init__(self, matches: bool = True) -> None:
        self.matches = matches
        self.national_id_hash: str | None = None

    async def has_matching_credential(self, national_id_hash: str) -> bool:
        self.national_id_hash = national_id_hash
        return self.matches


class RecordingOwnerRepository:
    def __init__(self, owner: Owner) -> None:
        self.owner = owner
        self.arguments: dict[str, Any] | None = None

    async def mark_ekyc_verified(self, **kwargs: Any) -> Owner:
        self.arguments = kwargs
        return self.owner


@pytest.mark.asyncio
async def test_ekyc_persists_only_the_canonical_hash() -> None:
    owner = Owner.model_construct(
        id=PydanticObjectId("507f1f77bcf86cd799439011"),
        email="owner@example.com",
        status=OwnerStatus.ACTIVE,
    )
    ekyc_repository = MatchingEkycRepository()
    owner_repository = RecordingOwnerRepository(owner)
    service = EkycVerificationService(
        cast(EkycRepository, ekyc_repository),
        cast(OwnerRepository, owner_repository),
    )

    result = await service.verify_owner_national_id(
        owner=owner,
        national_id="079-203-001234",
        secret="ekyc-test-secret",
    )

    assert result is owner
    assert owner_repository.arguments is not None
    assert owner_repository.arguments["owner_id"] == owner.id
    assert owner_repository.arguments["national_id_hash"] == hash_national_id(
        "079203001234",
        "ekyc-test-secret",
    )
    assert isinstance(owner_repository.arguments["verified_at"], datetime)
    assert "national_id" not in owner_repository.arguments


@pytest.mark.asyncio
async def test_ekyc_rejects_deleted_credential_match() -> None:
    owner = Owner.model_construct(
        id=PydanticObjectId("507f1f77bcf86cd799439011"),
        email="owner@example.com",
        status=OwnerStatus.ACTIVE,
    )
    ekyc_repository = MatchingEkycRepository(matches=False)
    owner_repository = RecordingOwnerRepository(owner)
    service = EkycVerificationService(
        cast(EkycRepository, ekyc_repository),
        cast(OwnerRepository, owner_repository),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.verify_owner_national_id(
            owner=owner,
            national_id="079203001234",
            secret="ekyc-test-secret",
        )

    assert exc_info.value.status_code == 403
    assert owner_repository.arguments is None


@pytest.mark.asyncio
async def test_ekyc_same_hash_is_idempotent() -> None:
    existing_hash = hash_national_id("079203001234", "ekyc-test-secret")
    owner = Owner.model_construct(
        id=PydanticObjectId("507f1f77bcf86cd799439011"),
        email="owner@example.com",
        status=OwnerStatus.ACTIVE,
        ekyc_verified=True,
        verified_national_id_hash=existing_hash,
    )
    ekyc_repository = MatchingEkycRepository()
    owner_repository = RecordingOwnerRepository(owner)
    service = EkycVerificationService(
        cast(EkycRepository, ekyc_repository),
        cast(OwnerRepository, owner_repository),
    )

    result = await service.verify_owner_national_id(
        owner=owner,
        national_id="079-203-001234",
        secret="ekyc-test-secret",
    )

    assert result is owner
    assert ekyc_repository.national_id_hash is None
    assert owner_repository.arguments is None


@pytest.mark.asyncio
async def test_ekyc_rejects_identity_overwrite() -> None:
    owner = Owner.model_construct(
        id=PydanticObjectId("507f1f77bcf86cd799439011"),
        email="owner@example.com",
        status=OwnerStatus.ACTIVE,
        ekyc_verified=True,
        verified_national_id_hash="b" * 64,
    )
    ekyc_repository = MatchingEkycRepository()
    owner_repository = RecordingOwnerRepository(owner)
    service = EkycVerificationService(
        cast(EkycRepository, ekyc_repository),
        cast(OwnerRepository, owner_repository),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.verify_owner_national_id(
            owner=owner,
            national_id="079203001234",
            secret="ekyc-test-secret",
        )

    assert exc_info.value.status_code == 409
    assert ekyc_repository.national_id_hash is None
    assert owner_repository.arguments is None


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
    ekyc_repository = MatchingEkycRepository()
    owner_repository = RecordingOwnerRepository(owner)
    service = EkycVerificationService(
        cast(EkycRepository, ekyc_repository),
        cast(OwnerRepository, owner_repository),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.verify_owner_national_id(
            owner=owner,
            national_id="079203001234",
            secret="ekyc-test-secret",
        )

    assert exc_info.value.status_code == 403
    assert ekyc_repository.national_id_hash is None
    assert owner_repository.arguments is None
