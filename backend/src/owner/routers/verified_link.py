from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.auth.dependencies import require_current_actor
from src.credential.schemas import (
    CreateVerifiedLinkRequest,
    RevokeVerifiedLinkResponse,
    VerifiedLinkCreatedResponse,
    VerifiedLinkListResponse,
    VerifiedLinkResponse,
)
from src.credential.services import verified_link as verified_link_service
from src.owner.models import Owner
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/owner/verified-links", tags=["Owner - Verified Links"])


@router.post(
    "",
    response_model=ApiResponse[VerifiedLinkCreatedResponse],
    status_code=status.HTTP_201_CREATED,
    summary="[Owner] Create Verification Code",
    description="Generate a shareable verification code for a claimed credential with optional expiration, allowed orgs, and max access count.",
)
async def create_verified_link(
    payload: CreateVerifiedLinkRequest,
    actor_info: Annotated[tuple, Depends(require_current_actor)],
) -> ApiResponse[VerifiedLinkCreatedResponse]:
    actor, _, actor_type = actor_info
    owner: Owner = actor  # type: ignore

    link, plaintext_code = await verified_link_service.create_verified_link(
        owner_id=owner.id,
        payload=payload,
    )

    data = VerifiedLinkCreatedResponse(
        id=str(link.id),
        code=plaintext_code,
        credential_id=str(link.credential_id),
        consent_mode=link.consent_mode,
        expires_at=link.expires_at,
        allowed_org_ids=[str(org_id) for org_id in link.allowed_org_ids],
        max_access_count=link.max_access_count,
        remaining_access_count=link.remaining_access_count,
        display_status=verified_link_service.derive_display_status(link),
        created_at=link.created_at,
        revoked_at=link.revoked_at,
    )

    return ApiResponse[VerifiedLinkCreatedResponse](
        success=True,
        data=data,
        message="Verification code created successfully.",
        error_code=None,
    )


@router.get(
    "",
    response_model=ApiResponse[VerifiedLinkListResponse],
    status_code=status.HTTP_200_OK,
    summary="[Owner] List Verification Codes",
    description="List all verification codes created by the authenticated owner.",
)
async def list_verified_links(
    actor_info: Annotated[tuple, Depends(require_current_actor)],
    credential_id: str | None = Query(default=None, description="Optional filter by credential ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[VerifiedLinkListResponse]:
    actor, _, _ = actor_info
    owner: Owner = actor  # type: ignore

    data = await verified_link_service.list_verified_links(
        owner_id=owner.id,
        credential_id=credential_id,
        page=page,
        page_size=page_size,
    )

    return ApiResponse[VerifiedLinkListResponse](
        success=True,
        data=data,
        message=None,
        error_code=None,
    )




@router.delete(
    "/{link_id}/revoke",
    response_model=ApiResponse[RevokeVerifiedLinkResponse],
    status_code=status.HTTP_200_OK,
    summary="[Owner] Revoke Verification Code",
    description="Revoke an active verification code so it can no longer be used for verification.",
)
async def revoke_verified_link(
    link_id: str,
    actor_info: Annotated[tuple, Depends(require_current_actor)],
) -> ApiResponse[RevokeVerifiedLinkResponse]:
    actor, _, _ = actor_info
    owner: Owner = actor  # type: ignore

    link = await verified_link_service.revoke_verified_link(
        owner_id=owner.id,
        link_id=link_id,
    )

    data = RevokeVerifiedLinkResponse(
        id=str(link.id),
        status="revoked",
        revoked_at=link.revoked_at or link.created_at,
    )

    return ApiResponse[RevokeVerifiedLinkResponse](
        success=True,
        data=data,
        message="Verification code revoked.",
        error_code=None,
    )
