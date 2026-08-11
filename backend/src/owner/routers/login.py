from fastapi import APIRouter, Request, status

from src.auth.models import DeviceInfo
from src.owner.schemas import (
    OwnerLoginRequest,
    OwnerLoginResponseData,
    OwnerVerifyLoginOtpRequest,
    OwnerVerifyLoginOtpResponseData,
)
from src.owner.services import owner_login_service
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/owner", tags=["Owner"])


@router.post(
    "/login",
    response_model=ApiResponse[OwnerLoginResponseData],
    status_code=status.HTTP_200_OK,
    summary="Login as an owner",
    description="Authenticates owner email and password, sending an OTP verification email and returning a temporary token.",
)
async def login_owner(
    payload: OwnerLoginRequest,
) -> ApiResponse[OwnerLoginResponseData]:
    otp_token, role = await owner_login_service.login(
        email=payload.email,
        password=payload.password,
        sending_email=payload.sendingemail,
    )

    return ApiResponse[OwnerLoginResponseData](
        success=True,
        data=OwnerLoginResponseData(otp_token=otp_token, role=role),
        message="Verification OTP sent to your email.",
        error_code=None,
    )


@router.post(
    "/login/verify-otp",
    response_model=ApiResponse[OwnerVerifyLoginOtpResponseData],
    status_code=status.HTTP_200_OK,
    summary="Verify OTP and complete login session",
    description="Verifies the OTP sent via email and the temporary token to issue the active access and refresh tokens.",
)
async def verify_login_otp(
    request: Request,
    payload: OwnerVerifyLoginOtpRequest,
) -> ApiResponse[OwnerVerifyLoginOtpResponseData]:
    user_agent = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    device_info = DeviceInfo(user_agent=user_agent, ip=ip)

    owner, access_token, refresh_token, refresh_token_expires_at = await owner_login_service.verify_otp_and_login(
        otp_token=payload.otp_token,
        otp_code=payload.otp_code,
        device_info=device_info,
    )

    return ApiResponse[OwnerVerifyLoginOtpResponseData](
        success=True,
        data=OwnerVerifyLoginOtpResponseData(
            access_token=access_token,
            refresh_token=refresh_token,
            refresh_token_expires_at=refresh_token_expires_at,
            owner_id=str(owner.id),
            email=owner.email,
        ),
        message="Logged in successfully.",
        error_code=None,
    )
