from beanie import PydanticObjectId

from src.credential.exceptions import InvalidOwnerAccountError
from src.ekyc.repository import EkycRepository
from src.owner.models import Owner


def owner_id(owner: Owner) -> PydanticObjectId:
    if owner.id is None:
        raise InvalidOwnerAccountError()
    return owner.id


async def verified_national_id_hash(
    owner: Owner,
    repository: EkycRepository,
) -> str | None:
    identity = await repository.get_verified_identity(owner_id(owner))
    return identity.national_id_hash if identity is not None else None
