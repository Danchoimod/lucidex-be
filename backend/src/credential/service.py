from math import ceil
from typing import Any

from beanie import PydanticObjectId
from fastapi import HTTPException, status

from src.credential.config import get_national_id_hash_secret
from src.credential.constants import CredentialStatus
from src.credential.repository import CredentialRepository, credential_repository
from src.credential.schemas import (
    ClaimCredentialData,
    ClaimedCredentialData,
    OwnerCredentialDetail,
    OwnerCredentialListData,
    OwnerCredentialListItem,
    OwnerCredentialListQuery,
    OwnerCredentialPagination,
    OwnerCredentialSummary,
)
from src.models import utc_now
from src.owner.constants import OwnerStatus
from src.owner.models import Owner
from src.utils.hashing import hash_national_id


def hash_imported_national_id(
    national_id: str,
    *,
    secret: str | None = None,
) -> str:
    """Create the canonical hash persisted by credential import."""
    return hash_national_id(
        national_id,
        secret or get_national_id_hash_secret(),
    )


def _owner_id(owner: Owner) -> PydanticObjectId:
    if owner.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid owner account.",
        )
    return owner.id


def _mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    visible_digits = 4
    if len(phone) <= visible_digits:
        return "*" * len(phone)
    return f"{'*' * (len(phone) - visible_digits)}{phone[-visible_digits:]}"


class OwnerCredentialService:
    def __init__(self, repository: CredentialRepository) -> None:
        self._repository = repository

    async def list_credentials(
        self,
        *,
        owner: Owner,
        query: OwnerCredentialListQuery,
    ) -> OwnerCredentialListData:
        owner_id = _owner_id(owner)
        sort_field, sort_direction = query.sort_parts()
        result = await self._repository.list_for_owner(
            owner_id=owner_id,
            verified_national_id_hash=owner.verified_national_id_hash,
            page=query.page,
            limit=query.limit,
            student_id=query.student_id,
            graduation_year=query.graduation_year,
            status=query.status,
            search=query.search,
            sort_field=sort_field,
            sort_direction=sort_direction,
        )
        items = [
            OwnerCredentialListItem(
                id=str(item["_id"]),
                student_id=item["student_id"],
                full_name=item["full_name"],
                graduation_year=item["graduation_year"],
                status=item["status"],
                can_claim=(
                    item["status"] == CredentialStatus.UNCLAIMED.value
                    and item.get("owner_id") is None
                ),
                claimed_at=item.get("claimed_at"),
            )
            for item in result.items
        ]
        total_pages = (
            ceil(result.total_credentials / query.limit)
            if result.total_credentials
            else 0
        )
        return OwnerCredentialListData(
            summary=OwnerCredentialSummary(
                total_credentials=result.total_credentials,
                total_claimed=result.total_claimed,
                total_unclaimed=result.total_unclaimed,
            ),
            items=items,
            pagination=OwnerCredentialPagination(
                page=query.page,
                limit=query.limit,
                total_items=result.total_credentials,
                total_pages=total_pages,
            ),
        )

    async def get_credential(
        self,
        *,
        owner: Owner,
        credential_id: PydanticObjectId,
    ) -> OwnerCredentialDetail:
        credential = await self._repository.get_for_owner(
            credential_id=credential_id,
            owner_id=_owner_id(owner),
            verified_national_id_hash=owner.verified_national_id_hash,
        )
        if credential is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found.",
            )
        return OwnerCredentialDetail(
            id=str(credential["_id"]),
            issuer_org_id=str(credential["issuer_org_id"]),
            student_id=credential["student_id"],
            full_name=credential["full_name"],
            dob=credential["dob"],
            major=credential["major"],
            graduation_year=credential["graduation_year"],
            classification=credential["classification"],
            university_email=credential["university_email"],
            phone=_mask_phone(credential.get("phone")),
            status=credential["status"],
            claim_method=credential.get("claim_method"),
            claimed_at=credential.get("claimed_at"),
        )

    async def claim_credential(
        self,
        *,
        owner: Owner,
        credential_id: PydanticObjectId,
    ) -> ClaimCredentialData:
        if owner.status != OwnerStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Owner account must be active.",
            )
        if not owner.ekyc_verified or not owner.verified_national_id_hash:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="eKYC verification is required.",
            )

        owner_id = _owner_id(owner)
        claimed = await self._repository.claim_for_owner(
            credential_id=credential_id,
            owner_id=owner_id,
            verified_national_id_hash=owner.verified_national_id_hash,
            claimed_at=utc_now(),
        )
        if claimed is not None:
            return self._claim_data(claimed, already_claimed=False)

        state = await self._repository.get_claim_state(credential_id)
        if state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found.",
            )
        if (
            state.get("status") == CredentialStatus.CLAIMED.value
            and state.get("owner_id") == owner_id
        ):
            return self._claim_data(state, already_claimed=True)
        if (
            state.get("status") == CredentialStatus.CLAIMED.value
            and state.get("owner_id") != owner_id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Credential was already claimed.",
            )
        if state.get("national_id_hash") != owner.verified_national_id_hash:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Credential does not match the verified identity.",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Credential is not claimable.",
        )

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


owner_credential_service = OwnerCredentialService(credential_repository)
