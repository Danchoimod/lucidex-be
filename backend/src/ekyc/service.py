from fastapi import HTTPException, status

from src.credential.config import get_national_id_hash_secret
from src.ekyc.repository import EkycRepository, ekyc_repository
from src.models import utc_now
from src.owner.constants import OwnerStatus
from src.owner.models import Owner
from src.owner.repository import OwnerRepository, owner_repository
from src.utils.hashing import hash_national_id


class EkycVerificationService:
    def __init__(
        self,
        repository: EkycRepository,
        owners: OwnerRepository,
    ) -> None:
        self._repository = repository
        self._owners = owners

    async def verify_owner_national_id(
        self,
        *,
        owner: Owner,
        national_id: str,
        secret: str | None = None,
    ) -> Owner:
        """Persist an internal verified hash, not a full provider eKYC flow."""
        if owner.status != OwnerStatus.ACTIVE or owner.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active owner account is required.",
            )
        national_id_hash = hash_national_id(
            national_id,
            secret or get_national_id_hash_secret(),
        )
        if (
            owner.verified_national_id_hash is not None
            and owner.verified_national_id_hash != national_id_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Verified identity cannot be changed in this flow.",
            )
        if owner.verified_national_id_hash == national_id_hash:
            return owner
        if not await self._repository.has_matching_credential(national_id_hash):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="National ID does not match an issued credential.",
            )
        if owner.id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid owner account.",
            )
        verified_owner = await self._owners.mark_ekyc_verified(
            owner_id=owner.id,
            national_id_hash=national_id_hash,
            verified_at=utc_now(),
        )
        if verified_owner is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Verified identity could not be persisted.",
            )
        return verified_owner


ekyc_verification_service = EkycVerificationService(
    ekyc_repository,
    owner_repository,
)
