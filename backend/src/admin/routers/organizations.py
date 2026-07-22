from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Request, status

from src.admin.dependencies import require_admin
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
