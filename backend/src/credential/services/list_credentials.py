from math import ceil

from src.credential.constants import CredentialStatus
from src.credential.repository import CredentialRepository, credential_repository
from src.credential.schemas import (
    OwnerCredentialListData,
    OwnerCredentialListItem,
    OwnerCredentialListQuery,
    OwnerCredentialPagination,
    OwnerCredentialSummary,
)
from src.credential.services.common import owner_id, verified_national_id_hash
from src.ekyc.repository import EkycRepository, ekyc_repository
from src.owner.models import Owner


class OwnerCredentialListService:
    def __init__(
        self,
        repository: CredentialRepository,
        identities: EkycRepository,
    ) -> None:
        self._repository = repository
        self._identities = identities

    async def list_credentials(
        self,
        *,
        owner: Owner,
        query: OwnerCredentialListQuery,
    ) -> OwnerCredentialListData:
        sort_field, sort_direction = query.sort_parts()
        identity_hash = await verified_national_id_hash(owner, self._identities)
        result = await self._repository.list_for_owner(
            owner_id=owner_id(owner),
            verified_national_id_hash=identity_hash,
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


owner_credential_list_service = OwnerCredentialListService(
    credential_repository,
    ekyc_repository,
)
