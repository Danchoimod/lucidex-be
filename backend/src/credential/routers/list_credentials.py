from typing import Annotated

from fastapi import APIRouter, Query, status

from src.credential.dependencies import CurrentOwner
from src.credential.routers.responses import COMMON_ERROR_RESPONSES
from src.credential.schemas import OwnerCredentialListData, OwnerCredentialListQuery
from src.credential.services import owner_credential_list_service
from src.schemas.common import ApiResponse

router = APIRouter()

LIST_RESPONSE_EXAMPLE = {
    "success": True,
    "data": {
        "summary": {
            "total_credentials": 2,
            "total_claimed": 1,
            "total_unclaimed": 1,
        },
        "items": [
            {
                "id": "507f1f77bcf86cd799439013",
                "student_id": "B2203243",
                "full_name": "Nguyen Van A",
                "graduation_year": 2023,
                "status": "unclaimed",
                "can_claim": True,
                "claimed_at": None,
            }
        ],
        "pagination": {
            "page": 1,
            "limit": 20,
            "total_items": 2,
            "total_pages": 1,
        },
    },
    "message": "Credentials fetched successfully.",
    "error_code": None,
}


@router.get(
    "/credentials",
    response_model=ApiResponse[OwnerCredentialListData],
    status_code=status.HTTP_200_OK,
    summary="List credentials available to the current owner",
    description=(
        "Returns credentials already claimed by the current owner together "
        "with unclaimed credentials matching the owner's verified national-ID "
        "hash. Security scope is applied before filtering and pagination."
    ),
    responses={
        200: {
            "description": "Authorized credential list.",
            "content": {"application/json": {"example": LIST_RESPONSE_EXAMPLE}},
        },
        **COMMON_ERROR_RESPONSES,
    },
)
async def list_owner_credentials(
    owner: CurrentOwner,
    query: Annotated[OwnerCredentialListQuery, Query()],
) -> ApiResponse[OwnerCredentialListData]:
    data = await owner_credential_list_service.list_credentials(
        owner=owner,
        query=query,
    )
    return ApiResponse(
        success=True,
        data=data,
        message="Credentials fetched successfully.",
        error_code=None,
    )
