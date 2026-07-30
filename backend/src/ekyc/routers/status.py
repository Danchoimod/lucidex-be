from fastapi import APIRouter, status

from src.credential.dependencies import CurrentOwner
from src.ekyc.schemas import OwnerEkycStatusData
from src.ekyc.services import owner_ekyc_status_service
from src.schemas.common import ApiResponse

router = APIRouter()

STATUS_RESPONSE_EXAMPLE = {
    "success": True,
    "data": {
        "status": "verified",
        "verification_id": "507f1f77bcf86cd799439015",
        "provider": "vnpt",
        "verified_at": "2026-07-28T09:30:00Z",
    },
    "message": "Owner eKYC status retrieved successfully.",
    "error_code": None,
}

STATUS_ERROR_RESPONSES = {
    401: {"description": "UNAUTHORIZED: invalid or expired access token."},
    403: {"description": "OWNER_ACCESS_REQUIRED or OWNER_INACTIVE."},
    404: {"description": "OWNER_NOT_FOUND."},
    500: {"description": "INTERNAL_SERVER_ERROR."},
}


@router.get(
    "/status",
    response_model=ApiResponse[OwnerEkycStatusData],
    status_code=status.HTTP_200_OK,
    summary="Get the current Owner eKYC status",
    description=(
        "Returns the authenticated Owner's current eKYC status. Owners without "
        "a verified eKYC identity receive status not_verified."
    ),
    responses={
        200: {
            "description": "Current Owner eKYC status.",
            "content": {"application/json": {"example": STATUS_RESPONSE_EXAMPLE}},
        },
        **STATUS_ERROR_RESPONSES,
    },
)
async def get_owner_ekyc_status(
    owner: CurrentOwner,
) -> ApiResponse[OwnerEkycStatusData]:
    data = await owner_ekyc_status_service.get_status(owner=owner)
    return ApiResponse(
        success=True,
        data=data,
        message="Owner eKYC status retrieved successfully.",
        error_code=None,
    )
