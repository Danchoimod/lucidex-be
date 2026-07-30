from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Path, status

from src.credential.dependencies import CurrentOwner
from src.credential.routers.responses import DETAIL_ERROR_RESPONSES
from src.credential.schemas import OwnerCredentialDetail
from src.credential.services import owner_credential_detail_service
from src.schemas.common import ApiResponse

router = APIRouter()

DETAIL_RESPONSE_EXAMPLE = {
    "success": True,
    "data": {
        "id": "507f1f77bcf86cd799439013",
        "issuer_org_id": "507f1f77bcf86cd799439014",
        "issuer": {
            "id": "507f1f77bcf86cd799439014",
            "name": "Lucidex University",
            "address": "1 Education Street",
            "contact_email": "contact@lucidex.edu.vn",
            "contact_phone": "02812345678",
        },
        "student_id": "B2203243",
        "full_name": "Nguyen Van A",
        "dob": "2001-01-01",
        "major": "Computer Science",
        "graduation_year": 2023,
        "classification": "Good",
        "university_email": "student@example.edu",
        "phone": "******5678",
        "status": "claimed",
        "claim_method": "manual",
        "claimed_at": "2026-07-29T10:00:00Z",
    },
    "message": "Credential fetched successfully.",
    "error_code": None,
}


@router.get(
    "/credentials/{credential_id}",
    response_model=ApiResponse[OwnerCredentialDetail],
    status_code=status.HTTP_200_OK,
    summary="Get a credential available to the current owner",
    description=(
        "Returns one credential only when its ID and owner security scope "
        "match in the same database query. Includes the Issuer's public "
        "organization profile. Out-of-scope credentials are reported as "
        "not found."
    ),
    responses={
        200: {
            "description": "Authorized credential detail.",
            "content": {"application/json": {"example": DETAIL_RESPONSE_EXAMPLE}},
        },
        **DETAIL_ERROR_RESPONSES,
    },
)
async def get_owner_credential(
    credential_id: Annotated[
        PydanticObjectId,
        Path(description="MongoDB ObjectId of the credential."),
    ],
    owner: CurrentOwner,
) -> ApiResponse[OwnerCredentialDetail]:
    data = await owner_credential_detail_service.get_credential(
        owner=owner,
        credential_id=credential_id,
    )
    return ApiResponse(
        success=True,
        data=data,
        message="Credential fetched successfully.",
        error_code=None,
    )
