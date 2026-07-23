from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query, Request, status

from src.admin.dependencies import require_admin
from src.admin.models import PlatformAdmin
from src.admin.schemas import RejectOrganizationRequest
from src.admin.services.organizations import (
    ApproveOrganizationData,
    RejectOrganizationData,
    approve_organization,
    list_organizations,
    reject_organization,
)
from src.organization.constants import OrganizationStatus, OrganizationType
from src.organization.schemas import OrganizationResponse
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/admin/organizations", tags=["Admin Organizations"])


@router.get(
    "/list",
    response_model=ApiResponse[list[OrganizationResponse]],
    status_code=status.HTTP_200_OK,
    summary="List organizations for admin review (oldest first)",
    description=(
        "Requires Platform Admin authentication. "
        "Retrieves submitted organizations ordered by creation date (oldest first). "
        "Filter by 'type' ('issuer' or 'verifier') and 'status' (defaults to 'pending_review')."
    ),
    responses={
        401: {"description": "Missing, invalid, expired, or unverified Admin session."},
    },
)
@router.get(
    "",
    response_model=ApiResponse[list[OrganizationResponse]],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def list_organizations_endpoint(
    type: OrganizationType | None = Query(
        default=None,
        description="Filter by organization type ('issuer' or 'verifier')",
    ),
    status_filter: OrganizationStatus | None = Query(
        default=OrganizationStatus.PENDING_REVIEW,
        alias="status",
        description="Filter by organization status (defaults to 'pending_review')",
    ),
    admin: PlatformAdmin = Depends(require_admin),
) -> ApiResponse[list[OrganizationResponse]]:
    organizations = await list_organizations(
        status=status_filter,
        org_type=type,
    )
    return ApiResponse(
        success=True,
        data=organizations,
        message="Organizations retrieved successfully.",
    )



@router.post(
    "/{organization_id}/approve",
    response_model=ApiResponse[ApproveOrganizationData],
    status_code=status.HTTP_200_OK,
    summary="Approve an organization and send its institution invite",
    description=(
        "Requires a Super Admin or Operations Admin who has completed "
        "password and TOTP login. "
        "Use the returned access_token with Swagger's Authorize button or "
        "send it as 'Authorization: Bearer <access_token>'. This endpoint "
        "has no request body. It approves the organization, revokes its "
        "previous pending invite, creates a new 72-hour invite, and sends "
        "the invite link by email."
    ),
    responses={
        200: {
            "description": "Organization approved and invitation sent.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "organization_id": "507f1f77bcf86cd799439011",
                            "organization_status": "approved",
                            "invite_status": "pending",
                            "invite_expires_at": "2026-07-25T02:39:14.543Z",
                            "email_sent": True,
                        },
                        "message": "Organization approved and invitation sent.",
                        "error_code": None,
                    }
                }
            },
        },
        401: {
            "description": (
                "Bearer token is missing/invalid/expired, or the Admin session "
                "is inactive or not TOTP-verified "
                "(`INVALID_ADMIN_ACCESS_TOKEN`)."
            )
        },
        404: {
            "description": "Organization does not exist (`ORGANIZATION_NOT_FOUND`)."
        },
        409: {
            "description": (
                "Organization state or concurrent invite/approval update "
                "prevents approval (`ORGANIZATION_NOT_APPROVABLE`, "
                "`ORGANIZATION_APPROVAL_CONFLICT`, or "
                "`INVITATION_ROTATION_CONFLICT`)."
            )
        },
        502: {
            "description": (
                "Invitation email delivery failed and the newly issued invite "
                "was revoked (`INVITATION_EMAIL_FAILED`)."
            )
        },
    },
)
async def approve_organization_endpoint(
    organization_id: PydanticObjectId,
    request: Request,
    admin: PlatformAdmin = Depends(require_admin),
) -> ApiResponse[ApproveOrganizationData]:
    data = await approve_organization(
        organization_id=organization_id,
        admin=admin,
        request_id=getattr(request.state, "request_id", None),
    )
    return ApiResponse(
        success=True,
        data=data,
        message="Organization approved and invitation sent.",
    )


@router.post(
    "/{organization_id}/reject",
    response_model=ApiResponse[RejectOrganizationData],
    status_code=status.HTTP_200_OK,
    summary="Reject an organization application",
    description=(
        "Rejects a pending organization application with a required reason. "
        "The decision is final and cannot be changed."
    ),
    responses={
        401: {"description": "Missing, invalid, or expired Admin access token."},
        404: {"description": "Organization does not exist."},
        409: {"description": "Organization already has a final decision."},
        422: {"description": "A non-empty rejection reason is required."},
        500: {"description": "Notification or audit persistence failed."},
        502: {"description": "Rejection email delivery failed."},
    },
)
async def reject_organization_endpoint(
    organization_id: PydanticObjectId,
    request: Request,
    payload: RejectOrganizationRequest | None = None,
    admin: PlatformAdmin = Depends(require_admin),
) -> ApiResponse[RejectOrganizationData]:
    data = await reject_organization(
        organization_id=organization_id,
        reason=payload.reason if payload else None,
        admin=admin,
        request_id=getattr(request.state, "request_id", None),
    )
    return ApiResponse(
        success=True,
        data=data,
        message="Organization application rejected.",
    )
