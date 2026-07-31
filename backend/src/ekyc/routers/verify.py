from fastapi import APIRouter, status

from src.credential.dependencies import CurrentOwner
from src.ekyc.routers.responses import VERIFY_ERROR_RESPONSES
from src.ekyc.schemas import VerifyOwnerEkycData, VerifyOwnerEkycRequest
from src.ekyc.services import ekyc_verification_service
from src.ekyc.services.vnpt_config import vnpt_ekyc_config_service
from src.schemas.common import ApiResponse

router = APIRouter()

VERIFY_RESPONSE_EXAMPLE = {
    "success": True,
    "data": {
        "identity_matched": True,
        "ekyc_status": "verified",
        "verified_at": "2026-07-29T09:30:00Z",
    },
    "message": "Identity verified successfully.",
    "error_code": None,
}


@router.post(
    "/verify",
    response_model=ApiResponse[VerifyOwnerEkycData],
    status_code=status.HTTP_200_OK,
    summary="Verify an Owner identity against an eligible credential",
    description=(
        "Validates the submitted VNPT access token against the platform VNPT "
        "configuration before hashing and binding the submitted national ID "
        "to the authenticated Owner. This is not provider or liveness eKYC."
    ),
    responses={
        200: {
            "description": "Identity matched and verified.",
            "content": {"application/json": {"example": VERIFY_RESPONSE_EXAMPLE}},
        },
        **VERIFY_ERROR_RESPONSES,
    },
)
async def verify_owner_ekyc(
    payload: VerifyOwnerEkycRequest,
    owner: CurrentOwner,
) -> ApiResponse[VerifyOwnerEkycData]:
    await vnpt_ekyc_config_service.require_valid_access_token(
        payload.access_token
    )
    data = await ekyc_verification_service.verify_owner_national_id(
        owner=owner,
        national_id=payload.national_id,
    )
    return ApiResponse(
        success=True,
        data=data,
        message="Identity verified successfully.",
        error_code=None,
    )
