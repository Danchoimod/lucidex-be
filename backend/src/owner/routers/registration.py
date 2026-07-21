from fastapi import APIRouter, status

from src.schemas.common import ApiResponse
from src.owner.schemas import (
    OwnerRegisterRequest,
    OwnerRegisterResponseData,
    OwnerVerifyOtpRequest,
    OwnerResendOtpRequest,
)
from src.owner.services import owner_registration_service

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


@router.post(
    "/verify-otp",
    response_model=ApiResponse[OwnerRegisterResponseData],
    status_code=status.HTTP_200_OK,
    summary="Verify OTP and activate owner account",
    description=(
        "Verifies the OTP sent to the owner's email and changes account status from pending to active."
    ),
)
async def verify_otp(
    payload: OwnerVerifyOtpRequest,
) -> ApiResponse[OwnerRegisterResponseData]:
    owner = await owner_registration_service.verify_and_activate(
        email=payload.email,
        otp_code=payload.otp_code,
    )
    return ApiResponse[OwnerRegisterResponseData](
        success=True,
        data=OwnerRegisterResponseData(
            id=str(owner.id),
            email=owner.email,
            status=owner.status,
        ),
        message="Account activated successfully.",
        error_code=None,
    )


@router.post(
    "/resend-otp",
    response_model=ApiResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Resend OTP and invalidate previous ones",
    description=(
        "Generates a new verification OTP and invalidates any currently active ones for the user."
    ),
)
async def resend_otp(
    payload: OwnerResendOtpRequest,
) -> ApiResponse[None]:
    await owner_registration_service.resend_otp(
        email=payload.email,
    )
    return ApiResponse[None](
        success=True,
        data=None,
        message="OTP resent successfully.",
        error_code=None,
    )
