"""Service for retrieving paginated and filtered issuer credential list."""

import math
import re
from typing import Any

from src.credential.models import Credential
from src.issuer.schemas import (
    CredentialListItemData,
    CredentialPaginationData,
    CredentialSummaryData,
    IssuerCredentialListData,
)
from src.organization.models import Organization


class CredentialListService:
    """Service handling credential listing, filtering, and summary calculations."""

    async def list_credentials(
        self,
        *,
        organization: Organization,
        page: int = 1,
        limit: int = 20,
        student_id: str | None = None,
        class_id: str | None = None,
        graduation_year: int | None = None,
        status: str | None = None,
        search: str | None = None,
        sort: str | None = None,
    ) -> IssuerCredentialListData:
        # 1. Base Query filter: scoped strictly to issuer organization and non-deleted
        query: dict[str, Any] = {
            "issuer_org_id": organization.id,
            "deleted_at": None,
        }

        if student_id and student_id.strip():
            query["student_id"] = student_id.strip()

        if class_id and class_id.strip():
            query["class_id"] = class_id.strip()

        if graduation_year is not None:
            query["graduation_year"] = graduation_year

        if status and status.strip():
            query["status"] = status.strip().lower()

        if search and search.strip():
            clean_search = search.strip()
            regex_pattern = f".*{re.escape(clean_search)}.*"
            query["$or"] = [
                {"student_id": {"$regex": regex_pattern, "$options": "i"}},
                {"full_name": {"$regex": regex_pattern, "$options": "i"}},
                {"university_email": {"$regex": regex_pattern, "$options": "i"}},
            ]

        # 2. Calculate summary metrics across the entire filtered dataset
        total_credentials = await Credential.find(query).count()

        query_claimed = {**query, "status": "claimed"}
        total_claimed = await Credential.find(query_claimed).count()

        query_unclaimed = {**query, "status": "unclaimed"}
        total_unclaimed = await Credential.find(query_unclaimed).count()

        summary_data = CredentialSummaryData(
            total_credentials=total_credentials,
            total_claimed=total_claimed,
            total_unclaimed=total_unclaimed,
        )

        # 3. Pagination math
        total_pages = math.ceil(total_credentials / limit) if total_credentials > 0 else 0
        skip = (page - 1) * limit

        pagination_data = CredentialPaginationData(
            page=page,
            limit=limit,
            total_items=total_credentials,
            total_pages=total_pages,
        )

        # 4. Sorting
        sort_field = "created_at"
        sort_dir = -1  # desc default

        sort_param = sort or "created_at:desc"
        if ":" in sort_param:
            field_part, dir_part = sort_param.split(":", 1)
            sort_field = field_part.strip()
            if dir_part.strip().lower() in ("desc", "-1"):
                sort_dir = -1
            elif dir_part.strip().lower() in ("asc", "1"):
                sort_dir = 1
        elif sort_param.startswith("-"):
            sort_field = sort_param[1:].strip()
            sort_dir = -1
        elif sort_param.startswith("+"):
            sort_field = sort_param[1:].strip()
            sort_dir = 1
        else:
            sort_field = sort_param.strip()
            sort_dir = -1

        # 5. Fetch items
        credentials = (
            await Credential.find(query)
            .sort((sort_field, sort_dir))
            .skip(skip)
            .limit(limit)
            .to_list()
        )

        items: list[CredentialListItemData] = []
        for c in credentials:
            claimed_at_val = (
                c.claimed_at.isoformat()
                if getattr(c, "claimed_at", None)
                else None
            )
            created_at_val = (
                c.created_at.isoformat()
                if getattr(c, "created_at", None)
                else None
            )

            items.append(
                CredentialListItemData(
                    id=str(c.id),
                    student_id=c.student_id,
                    class_id=c.class_id,
                    full_name=c.full_name,
                    graduation_year=c.graduation_year,
                    status=c.status,
                    claimed_at=claimed_at_val,
                    created_at=created_at_val,
                )
            )

        return IssuerCredentialListData(
            summary=summary_data,
            items=items,
            pagination=pagination_data,
        )


credential_list_service = CredentialListService()
