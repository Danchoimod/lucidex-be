from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Path, Query, status

from src.credential.dependencies import CurrentOwner
from src.credential.schemas import (
    ClaimCredentialData,
    ClaimCredentialRequest,
    OwnerCredentialDetail,
    OwnerCredentialListData,
    OwnerCredentialListQuery,
)
from src.credential.service import owner_credential_service
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/owner", tags=["Owner Credentials"])

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

DETAIL_RESPONSE_EXAMPLE = {
    "success": True,
    "data": {
        "id": "507f1f77bcf86cd799439013",
        "issuer_org_id": "507f1f77bcf86cd799439014",
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

COMMON_ERROR_RESPONSES = {
    401: {"description": "UNAUTHORIZED or HTTP_401."},
    403: {
        "description": (
            "HTTP_403 fallback: owner access, active account, eKYC, or "
            "national-ID match requirement failed."
        )
    },
    422: {"description": "VALIDATION_ERROR."},
    500: {"description": "INTERNAL_SERVER_ERROR."},
}

DETAIL_ERROR_RESPONSES = {
    **COMMON_ERROR_RESPONSES,
    404: {"description": "HTTP_404 fallback: credential is not in owner scope."},
}

CLAIM_ERROR_RESPONSES = {
    **DETAIL_ERROR_RESPONSES,
    409: {
        "description": (
            "HTTP_409 fallback: credential was claimed by another owner "
            "or is not claimable."
        )
    },
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
    data = await owner_credential_service.list_credentials(
        owner=owner,
        query=query,
    )
    return ApiResponse(
        success=True,
        data=data,
        message="Credentials fetched successfully.",
        error_code=None,
    )


@router.get(
    "/credentials/{credential_id}",
    response_model=ApiResponse[OwnerCredentialDetail],
    status_code=status.HTTP_200_OK,
    summary="Get a credential available to the current owner",
    description=(
        "Returns one credential only when its ID and owner security scope "
        "match in the same database query. Out-of-scope credentials are "
        "reported as not found."
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
    data = await owner_credential_service.get_credential(
        owner=owner,
        credential_id=credential_id,
    )
    return ApiResponse(
        success=True,
        data=data,
        message="Credential fetched successfully.",
        error_code=None,
    )


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
    data = await owner_credential_service.claim_credential(
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
