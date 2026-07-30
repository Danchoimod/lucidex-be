from beanie import PydanticObjectId

from src.credential.exceptions import InvalidOwnerAccountError
from src.ekyc.repository import EkycRepository
from src.owner.models import Owner


def owner_id(owner: Owner) -> PydanticObjectId:
    if owner.id is None:
        raise InvalidOwnerAccountError()
    return owner.id


def mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    visible_digits = 4
    if len(phone) <= visible_digits:
        return "*" * len(phone)
    return f"{'*' * (len(phone) - visible_digits)}{phone[-visible_digits:]}"


async def verified_national_id_hash(
    owner: Owner,
    repository: EkycRepository,
) -> str | None:
    identity = await repository.get_verified_identity(owner_id(owner))
    return identity.national_id_hash if identity is not None else None
