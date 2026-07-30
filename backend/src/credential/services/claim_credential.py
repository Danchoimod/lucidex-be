from typing import Any

from beanie import PydanticObjectId

from src.credential.constants import CredentialStatus
from src.credential.exceptions import (
    CredentialAlreadyClaimedError,
    CredentialIdentityMismatchError,
    CredentialNotClaimableError,
    CredentialNotFoundError,
    EkycVerificationRequiredError,
    OwnerInactiveError,
)
from src.credential.repository import CredentialRepository, credential_repository
from src.credential.schemas import ClaimCredentialData, ClaimedCredentialData
from src.credential.services.common import owner_id, verified_national_id_hash
from src.ekyc.repository import EkycRepository, ekyc_repository
from src.models import utc_now
from src.owner.constants import OwnerStatus
from src.owner.models import Owner


class OwnerCredentialClaimService:
    def __init__(
        self,
        repository: CredentialRepository,
        identities: EkycRepository,
    ) -> None:
        self._repository = repository
        self._identities = identities

    async def claim_credential(
        self,
        *,
        owner: Owner,
        credential_id: PydanticObjectId,
    ) -> ClaimCredentialData:
        if owner.status != OwnerStatus.ACTIVE:
            raise OwnerInactiveError()
        identity_hash = await verified_national_id_hash(owner, self._identities)
        if not identity_hash:
            raise EkycVerificationRequiredError()

        current_owner_id = owner_id(owner)
        claimed = await self._repository.claim_for_owner(
            credential_id=credential_id,
            owner_id=current_owner_id,
            verified_national_id_hash=identity_hash,
            claimed_at=utc_now(),
        )
        if claimed is not None:
            return self._claim_data(claimed, already_claimed=False)

        state = await self._repository.get_claim_state(credential_id)
        if state is None:
            raise CredentialNotFoundError()
        if (
            state.get("status") == CredentialStatus.CLAIMED.value
            and state.get("owner_id") == current_owner_id
        ):
            return self._claim_data(state, already_claimed=True)
        if (
            state.get("status") == CredentialStatus.CLAIMED.value
            and state.get("owner_id") != current_owner_id
        ):
            raise CredentialAlreadyClaimedError()
        if state.get("national_id_hash") != identity_hash:
            raise CredentialIdentityMismatchError()
        raise CredentialNotClaimableError()

    @staticmethod
    def _claim_data(
        credential: dict[str, Any],
        *,
        already_claimed: bool,
    ) -> ClaimCredentialData:
        return ClaimCredentialData(
            credential=ClaimedCredentialData(
                id=str(credential["_id"]),
                status=credential["status"],
                claim_method=credential.get("claim_method"),
                claimed_at=credential.get("claimed_at"),
            ),
            already_claimed=already_claimed,
        )


owner_credential_claim_service = OwnerCredentialClaimService(
    credential_repository,
    ekyc_repository,
)
