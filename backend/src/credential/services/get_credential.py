from beanie import PydanticObjectId

from src.credential.constants import DEFAULT_DEGREE_TYPE
from src.credential.exceptions import CredentialNotFoundError
from src.credential.repository import CredentialRepository, credential_repository
from src.credential.schemas import (
    OwnerCredentialDetail,
    OwnerCredentialIssuerDetail,
)
from src.credential.services.common import (
    owner_id,
    verified_national_id_hash,
)
from src.ekyc.repository import EkycRepository, ekyc_repository
from src.owner.models import Owner


class OwnerCredentialDetailService:
    def __init__(
        self,
        repository: CredentialRepository,
        identities: EkycRepository,
    ) -> None:
        self._repository = repository
        self._identities = identities

    async def get_credential(
        self,
        *,
        owner: Owner,
        credential_id: PydanticObjectId,
    ) -> OwnerCredentialDetail:
        identity_hash = await verified_national_id_hash(owner, self._identities)
        credential = await self._repository.get_for_owner(
            credential_id=credential_id,
            owner_id=owner_id(owner),
            verified_national_id_hash=identity_hash,
        )
        if credential is None:
            raise CredentialNotFoundError()
        issuer = credential.get("issuer")
        return OwnerCredentialDetail(
            id=str(credential["_id"]),
            issuer_org_id=str(credential["issuer_org_id"]),
            issuer=(
                OwnerCredentialIssuerDetail(
                    id=str(issuer["_id"]),
                    name=issuer["name"],
                    address=issuer["address"],
                    contact_email=issuer["contact_email"],
                    contact_phone=issuer["contact_phone"],
                )
                if issuer
                else None
            ),
            student_id=credential["student_id"],
            full_name=credential["full_name"],
            dob=credential["dob"],
            major=credential["major"],
            major_vi=credential.get("major_vi"),
            major_en=credential.get("major_en"),
            degree_type=credential.get("degree_type") or DEFAULT_DEGREE_TYPE,
            graduation_year=credential["graduation_year"],
            classification=credential["classification"],
            graduation_classification_vi=credential.get(
                "graduation_classification_vi"
            ),
            graduation_classification_en=credential.get(
                "graduation_classification_en"
            ),
            university_email=credential["university_email"],
            phone=credential.get("phone"),
            status=credential["status"],
            claim_method=credential.get("claim_method"),
            claimed_at=credential.get("claimed_at"),
        )


owner_credential_detail_service = OwnerCredentialDetailService(
    credential_repository,
    ekyc_repository,
)
