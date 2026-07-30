from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Path, status

from src.credential.dependencies import CurrentOwner
from src.credential.routers.responses import CLAIM_ERROR_RESPONSES
from src.credential.schemas import ClaimCredentialData, ClaimCredentialRequest
from src.credential.services import owner_credential_claim_service
from src.schemas.common import ApiResponse

router = APIRouter()

CLAIM_RESPONSE_EXAMPLE = {
    "success": True,
    "data": {
        "credential": {
            "id": "507f1f77bcf86cd799439013",
            "status": "claimed",
            "claim_method": "manual",
            "claimed_at": "2026-07-29T10:00:00Z",
        },
        "already_claimed": False,
    },
    "message": "Credential claimed successfully.",
    "error_code": None,
}


@router.post(
    "/claim/credentials/{credential_id}",
    response_model=ApiResponse[ClaimCredentialData],
    status_code=status.HTTP_200_OK,
    summary="Claim a credential using the verified national ID",
    description=(
        "Atomically claims an unclaimed credential whose national-ID hash "
        "matches the active owner's verified hash. Repeating the request as "
        "the same owner is idempotent."
    ),
    responses={
        200: {
            "description": "Credential claimed or already claimed by this owner.",
            "content": {"application/json": {"example": CLAIM_RESPONSE_EXAMPLE}},
        },
        **CLAIM_ERROR_RESPONSES,
    },
)
async def claim_owner_credential(
    credential_id: Annotated[
        PydanticObjectId,
        Path(description="MongoDB ObjectId of the credential."),
    ],
    owner: CurrentOwner,
    _payload: ClaimCredentialRequest,
) -> ApiResponse[ClaimCredentialData]:
    data = await owner_credential_claim_service.claim_credential(
        owner=owner,
        credential_id=credential_id,
    )
    message = (
        "Credential was already claimed by the current owner."
        if data.already_claimed
        else "Credential claimed successfully."
    )
    return ApiResponse(
        success=True,
        data=data,
        message=message,
        error_code=None,
    )
