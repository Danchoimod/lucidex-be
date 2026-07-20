from fastapi import APIRouter, Request, status

from src.admin.schemas import (
    AdminAccessTokenData,
    AdminLoginRequest,
    AdminLoginResponseData,
    AdminVerifyLoginRequest,
    AdminVerifySetupRequest,
)
from src.admin.services import admin_auth_service
from src.auth.models import DeviceInfo
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/admin/auth", tags=["Admin Auth"])


def _device_info(request: Request) -> DeviceInfo:
    return DeviceInfo(
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )


@router.post(
    "/login",
    response_model=ApiResponse[AdminLoginResponseData],
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
)
async def login_admin(
    payload: AdminLoginRequest,
) -> ApiResponse[AdminLoginResponseData]:
    data = await admin_auth_service.login(
        username=payload.username,
        password=payload.password,
    )
    return ApiResponse(
        success=True,
        data=data,
        message="Additional authentication is required.",
    )


@router.post(
    "/totp/setup/verify",
    response_model=ApiResponse[AdminAccessTokenData],
    status_code=status.HTTP_200_OK,
)
async def verify_totp_setup(
    request: Request,
    payload: AdminVerifySetupRequest,
) -> ApiResponse[AdminAccessTokenData]:
    data = await admin_auth_service.verify_setup(
        setup_token=payload.setup_token,
        otp_code=payload.otp_code,
        device_info=_device_info(request),
    )
    return ApiResponse(
        success=True,
        data=data,
        message="Logged in successfully.",
    )


@router.post(
    "/totp/login/verify",
    response_model=ApiResponse[AdminAccessTokenData],
    status_code=status.HTTP_200_OK,
)
async def verify_totp_login(
    request: Request,
    payload: AdminVerifyLoginRequest,
) -> ApiResponse[AdminAccessTokenData]:
    data = await admin_auth_service.verify_login(
        challenge_token=payload.challenge_token,
        otp_code=payload.otp_code,
        device_info=_device_info(request),
    )
    return ApiResponse(
        success=True,
        data=data,
        message="Logged in successfully.",
    )
