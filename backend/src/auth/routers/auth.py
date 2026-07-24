from fastapi import APIRouter, Request, status

from src.auth.models import DeviceInfo
from src.auth.schemas import (
    LoginRequest,
    LoginResponseData,
    VerifyLoginOtpRequest,
    VerifyLoginOtpResponseData,
    ResendOtpRequest,
    RefreshTokenRequest,
    RefreshTokenResponseData,
)
from src.auth.services import login_service, resend_otp_service, session_service
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=ApiResponse[LoginResponseData],
    status_code=status.HTTP_200_OK,
    summary="Login",
    description="Authenticates user email and password, sending an OTP verification email and returning a temporary token.",
    responses={
        401: {
            "description": "Unauthorized - Invalid email or password.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "Invalid email or password.",
                        "error_code": "INVALID_CREDENTIALS",
                    }
                }
            },
        },
        403: {
            "description": "Forbidden - Account is not active.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "Account is not active.",
                        "error_code": "INACTIVE_ACCOUNT",
                    }
                }
            },
        },
        404: {
            "description": "Not Found - Account does not exist.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "Account does not exist.",
                        "error_code": "ACCOUNT_NOT_FOUND",
                    }
                }
            },
        },
    },
)
async def login(
    payload: LoginRequest,
) -> ApiResponse[LoginResponseData]:
    otp_token, role = await login_service.login(
        email=payload.email,
        password=payload.password,
        sending_email=payload.sendingemail,
    )

    return ApiResponse[LoginResponseData](
        success=True,
        data=LoginResponseData(otp_token=otp_token, role=role),
        message="Verification OTP sent to your email.",
        error_code=None,
    )


@router.post(
    "/login/verify-otp",
    response_model=ApiResponse[VerifyLoginOtpResponseData],
    status_code=status.HTTP_200_OK,
    summary="Verify OTP and complete login session",
    description="Verifies the OTP sent via email and the temporary token to issue the active access and refresh tokens.",
    responses={
        400: {
            "description": "Bad Request - Invalid or expired OTP code.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "Invalid or expired OTP code.",
                        "error_code": "INVALID_OTP",
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Invalid or expired temporary token.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "Invalid or expired login session token.",
                        "error_code": "INVALID_CREDENTIALS",
                    }
                }
            },
        },
    },
)
async def verify_login_otp(
    request: Request,
    payload: VerifyLoginOtpRequest,
) -> ApiResponse[VerifyLoginOtpResponseData]:
    user_agent = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    device_info = DeviceInfo(user_agent=user_agent, ip=ip)

    user, access_token, refresh_token = await login_service.verify_otp_and_login(
        otp_token=payload.otp_token,
        otp_code=payload.otp_code,
        device_info=device_info,
    )

    return ApiResponse[VerifyLoginOtpResponseData](
        success=True,
        data=VerifyLoginOtpResponseData(
            access_token=access_token,
            refresh_token=refresh_token,
            owner_id=str(user.id),
            email=getattr(user, "email", ""),
        ),
        message="Logged in successfully.",
        error_code=None,
    )


@router.post(
    "/resend-otp",
    response_model=ApiResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Resend OTP and invalidate previous ones",
    description=(
        "Resends OTP via email. If account status is pending, sends verification OTP (VERIFY_EMAIL); "
        "if active, sends login OTP (LOGIN). Invalidates any previously issued active OTP for this user."
    ),
    responses={
        404: {
            "description": "Not Found - Account does not exist.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "Account does not exist.",
                        "error_code": "ACCOUNT_NOT_FOUND",
                    }
                }
            },
        },
    },
)
async def resend_otp(
    payload: ResendOtpRequest,
) -> ApiResponse[None]:
    await resend_otp_service.resend_otp(
        email=payload.email,
        token=payload.token,
    )
    return ApiResponse[None](
        success=True,
        data=None,
        message="OTP resent successfully.",
        error_code=None,
    )


@router.post(
    "/refresh",
    response_model=ApiResponse[RefreshTokenResponseData],
    status_code=status.HTTP_200_OK,
    summary="Refresh API Access Token",
    description="Validates a refresh token and issues a new short-lived access token.",
)
@router.post(
    "/refresh-token",
    response_model=ApiResponse[RefreshTokenResponseData],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def refresh_access_token(
    payload: RefreshTokenRequest,
) -> ApiResponse[RefreshTokenResponseData]:
    access_token, token_type = await session_service.refresh_access_token(
        refresh_token=payload.refresh_token,
    )
    return ApiResponse[RefreshTokenResponseData](
        success=True,
        data=RefreshTokenResponseData(
            access_token=access_token,
            token_type=token_type,
        ),
        message="Access token refreshed successfully.",
        error_code=None,
    )
