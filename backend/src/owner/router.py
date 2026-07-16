from fastapi import APIRouter, status

from src.schemas.common import ApiResponse
from src.owner.schemas import (
    OwnerRegisterRequest,
    OwnerRegisterResponseData,
)
from src.owner.service import owner_registration_service

router = APIRouter(prefix="/owner", tags=["Owner"])


@router.get(
    "/health",
    summary="Check owner API health",
    description=(
        "Allows clients to check whether the Owner API routes are available. "
        "Returns a success response when the portal router is reachable."
    ),
)
async def health_check():
    return {
        "success": True,
        "data": {"message": "Owner portal is running."},
        "message": "OK",
        "error_code": None,
    }


@router.post(
    "/register",
    response_model=ApiResponse[OwnerRegisterResponseData],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new owner",
    description=(
        "Allows a new Credential Owner to submit their registration form. "
        "Validates email uniqueness and password complexity, then directly creates the account."
    ),
)
async def register_owner(
    payload: OwnerRegisterRequest,
) -> ApiResponse[OwnerRegisterResponseData]:
    owner = await owner_registration_service.register(
        email=payload.email,
        password=payload.password,
        confirm_password=payload.confirm_password,
    )
    return ApiResponse[OwnerRegisterResponseData](
        success=True,
        data=OwnerRegisterResponseData(
            id=str(owner.id),
            email=owner.email,
            status=owner.status,
        ),
        message="Account created successfully.",
        error_code=None,
    )
