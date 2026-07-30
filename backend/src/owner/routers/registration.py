from fastapi import APIRouter, BackgroundTasks, status

from src.mailer import mailer_service
from src.owner.schemas import (
    OwnerRegisterRequest,
    OwnerRegisterResponseData,
    OwnerVerifyOtpRequest,
    OwnerVerifyOtpResponseData,
)
from src.owner.services import owner_registration_service
from src.schemas.common import ApiResponse

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
        full_name=payload.full_name,
        phone=payload.phone,
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
    response_model=ApiResponse[OwnerVerifyOtpResponseData],
    status_code=status.HTTP_200_OK,
    summary="Verify OTP and activate owner account",
    description=(
        "Verifies the OTP sent to the owner's email, activates the account, and issues authentication tokens."
    ),
)
async def verify_otp(
    payload: OwnerVerifyOtpRequest,
    background_tasks: BackgroundTasks,
) -> ApiResponse[OwnerVerifyOtpResponseData]:
    owner, access_token, refresh_token, refresh_token_expires_at = await owner_registration_service.verify_and_activate(
        email=payload.email,
        otp_code=payload.otp_code,
    )
    background_tasks.add_task(
        mailer_service.send_welcome_email,
        email=str(owner.email),
        owner_name=owner.full_name or "bạn",
    )
    return ApiResponse[OwnerVerifyOtpResponseData](
        success=True,
        data=OwnerVerifyOtpResponseData(
            id=str(owner.id),
            email=owner.email,
            status=owner.status,
            access_token=access_token,
            refresh_token=refresh_token,
            refresh_token_expires_at=refresh_token_expires_at,
            token_type="bearer",
        ),
        message="Account activated successfully.",
        error_code=None,
    )



