from src.ekyc.repository import EkycRepository, ekyc_repository
from src.ekyc.schemas import OwnerEkycStatusData
from src.owner.exceptions import OwnerNotFoundError
from src.owner.models import Owner


class OwnerEkycStatusService:
    def __init__(self, repository: EkycRepository) -> None:
        self._repository = repository

    async def get_status(self, *, owner: Owner) -> OwnerEkycStatusData:
        if owner.id is None:
            raise OwnerNotFoundError()

        identity = await self._repository.get_verified_identity(owner.id)
        if identity is None:
            return OwnerEkycStatusData(
                status="not_verified",
                verification_id=None,
                provider=None,
                verified_at=None,
            )

        return OwnerEkycStatusData(
            status="verified",
            verification_id=(
                str(identity.verification_id)
                if identity.verification_id is not None
                else None
            ),
            provider=identity.provider,
            verified_at=identity.verified_at,
        )


owner_ekyc_status_service = OwnerEkycStatusService(ekyc_repository)
