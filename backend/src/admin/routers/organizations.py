from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, status

from src.admin.dependencies import require_super_admin
from src.admin.models import PlatformAdmin
from src.admin.services.organizations import (
    ApproveOrganizationData,
    approve_organization,
)
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/admin/organizations", tags=["Admin Organizations"])


@router.post(
    "/{organization_id}/approve",
    response_model=ApiResponse[ApproveOrganizationData],
    status_code=status.HTTP_200_OK,
    summary="Approve an organization and send its institution invite",
    description=(
        "Requires a Super Admin who has completed password and TOTP login. "
        "Use the returned access_token with Swagger's Authorize button or "
        "send it as 'Authorization: Bearer <access_token>'. This endpoint "
        "has no request body. It approves the organization, revokes its "
        "previous pending invite, creates a new 72-hour invite, and sends "
        "the invite link by email."
    ),
    responses={
        401: {"description": "Missing, invalid, expired, or unverified Admin session."},
        403: {"description": "The authenticated Admin is not a Super Admin."},
        404: {"description": "Organization not found."},
        409: {"description": "Organization cannot be approved in its current state."},
        502: {"description": "Invitation email failed; the new invite was revoked."},
    },
)
async def approve_organization_endpoint(
    organization_id: PydanticObjectId,
    admin: PlatformAdmin = Depends(require_super_admin),
) -> ApiResponse[ApproveOrganizationData]:
    data = await approve_organization(
        organization_id=organization_id,
        admin=admin,
    )
    return ApiResponse(
        success=True,
        data=data,
        message="Organization approved and invitation sent.",
    )
