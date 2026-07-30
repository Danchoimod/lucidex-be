from datetime import datetime

from beanie import PydanticObjectId

from src.credential.config import get_national_id_hash_secret
from src.credential.exceptions import OwnerInactiveError
from src.ekyc.exceptions import (
    EkycPersistenceFailedError,
    EkycTimestampUnavailableError,
    IdentityAlreadyLinkedError,
    IdentityChangeNotAllowedError,
    InvalidNationalIdFormatError,
)
from src.ekyc.repository import (
    EkycIdentityState,
    EkycRepository,
    ekyc_repository,
)
from src.ekyc.schemas import VerifyOwnerEkycData
from src.models import utc_now
from src.owner.constants import OwnerStatus
from src.owner.exceptions import OwnerNotFoundError
from src.owner.models import Owner
from src.owner.repository import OwnerRepository, owner_repository
from src.utils.hashing import hash_national_id, normalize_national_id


class EkycVerificationService:
    def __init__(
        self,
        owners: OwnerRepository,
        repository: EkycRepository,
    ) -> None:
        self._owners = owners
        self._repository = repository

    async def verify_owner_national_id(
        self,
        *,
        owner: Owner,
        national_id: str,
        secret: str | None = None,
    ) -> VerifyOwnerEkycData:
        """Persist the verified Owner identity independently of credentials."""
        if owner.status != OwnerStatus.ACTIVE or owner.deleted_at is not None:
            raise OwnerInactiveError()
        try:
            normalized_national_id = normalize_national_id(national_id)
        except ValueError as exc:
            raise InvalidNationalIdFormatError() from exc
        national_id_hash = hash_national_id(
            normalized_national_id,
            secret or get_national_id_hash_secret(),
        )
        if owner.id is None:
            raise OwnerNotFoundError()
        try:
            legacy_hash = await self._owners.get_legacy_national_id_hash(owner.id)
        except Exception as exc:
            raise EkycPersistenceFailedError() from exc
        if legacy_hash is not None and legacy_hash != national_id_hash:
            raise IdentityChangeNotAllowedError()

        identity = await self._bind_identity(
            owner_id=owner.id,
            national_id_hash=national_id_hash,
            verified_at=utc_now(),
        )
        try:
            legacy_fields_cleared = await self._owners.clear_legacy_ekyc_fields(
                owner.id
            )
        except Exception as exc:
            raise EkycPersistenceFailedError() from exc
        if not legacy_fields_cleared:
            raise EkycPersistenceFailedError()
        return self._verified_data(identity.verified_at)

    async def _bind_identity(
        self,
        *,
        owner_id: PydanticObjectId,
        national_id_hash: str,
        verified_at: datetime,
    ) -> EkycIdentityState:
        try:
            identity = await self._repository.bind_verified_identity(
                owner_id=owner_id,
                national_id_hash=national_id_hash,
                verified_at=verified_at,
            )
        except Exception as exc:
            raise EkycPersistenceFailedError() from exc
        if identity is not None:
            return identity

        try:
            existing_owner_identity = (
                await self._repository.get_verified_identity(owner_id)
            )
            existing_hash_identity = (
                await self._repository.get_by_national_id_hash(national_id_hash)
            )
        except Exception as exc:
            raise EkycPersistenceFailedError() from exc
        if existing_owner_identity is not None:
            if existing_owner_identity.national_id_hash != national_id_hash:
                raise IdentityChangeNotAllowedError()
            return existing_owner_identity

        if (
            existing_hash_identity is not None
            and existing_hash_identity.owner_id != owner_id
        ):
            raise IdentityAlreadyLinkedError()
        raise EkycPersistenceFailedError()

    @staticmethod
    def _verified_data(verified_at: datetime | None) -> VerifyOwnerEkycData:
        if verified_at is None:
            raise EkycTimestampUnavailableError()
        return VerifyOwnerEkycData(
            identity_matched=True,
            ekyc_status="verified",
            verified_at=verified_at,
        )

ekyc_verification_service = EkycVerificationService(
    owner_repository,
    ekyc_repository,
)
