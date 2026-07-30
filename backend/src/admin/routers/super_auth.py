from fastapi import APIRouter, Request, status

from src.admin.exceptions import AdminLoginRateLimitError
from src.admin.rate_limit import admin_login_rate_limiter
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


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


@router.post(
    "/login",
    response_model=ApiResponse[AdminLoginResponseData],
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
    summary="Start Admin login",
    description=(
        "Validates the username and password for an active Super Admin or "
        "Operations Admin. Returns a setup token and TOTP enrollment data on "
        "first login, or a challenge token when TOTP is already enabled. "
        "Neither temporary token is an API access token."
    ),
    responses={
        401: {
            "description": (
                "Username/password is invalid or the Admin account is not "
                "eligible to log in (`INVALID_ADMIN_CREDENTIALS`)."
            )
        },
        422: {"description": "Username or password is missing or malformed."},
        403: {
            "description": (
                "The Admin account is not active "
                "(`INACTIVE_ADMIN_ACCOUNT`)."
            )
        },
        429: {
            "description": (
                "The client IP exceeded five login requests per minute "
                "(`ADMIN_LOGIN_RATE_LIMITED`)."
            )
        },
        500: {
            "description": (
                "The Admin account has an invalid authentication state "
                "(`ADMIN_AUTHENTICATION_STATE_ERROR`)."
            )
        },
    },
)
async def login_admin(
    request: Request,
    payload: AdminLoginRequest,
) -> ApiResponse[AdminLoginResponseData]:
    client_ip = request.client.host if request.client else "unknown"
    rate_limit = await admin_login_rate_limiter.consume(client_ip)
    if not rate_limit.allowed:
        raise AdminLoginRateLimitError(
            retry_after=rate_limit.retry_after,
            log_context={
                "auth_stage": "password",
                "failure_reason": "ip_rate_limit_exceeded",
            },
        )
    data = await admin_auth_service.login(
        username=payload.username,
        password=payload.password,
        request_id=_request_id(request),
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
    summary="Verify first-time Admin TOTP setup",
    description=(
        "Completes first-time TOTP enrollment using the setup token returned "
        "by `/admin/auth/login` and a six-digit authenticator code. On "
        "success, enables TOTP, creates a verified Admin session, and returns "
        "a bearer access token. The setup token is single-purpose and cannot "
        "be used to authorize Admin APIs."
    ),
    responses={
        401: {
            "description": (
                "Setup token is invalid/expired, the setup state changed, or "
                "the TOTP code is invalid (`INVALID_ADMIN_TOKEN` or "
                "`INVALID_AUTHENTICATION_CODE`)."
            )
        },
        403: {
            "description": (
                "The Admin account is locked or not active "
                "(`INACTIVE_ADMIN_ACCOUNT`)."
            )
        },
        422: {"description": "TOTP code is not exactly six digits."},
    },
)
async def verify_totp_setup(
    request: Request,
    payload: AdminVerifySetupRequest,
) -> ApiResponse[AdminAccessTokenData]:
    data = await admin_auth_service.verify_setup(
        setup_token=payload.setup_token,
        otp_code=payload.otp_code,
        device_info=_device_info(request),
        request_id=_request_id(request),
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
    summary="Verify Admin TOTP login",
    description=(
        "Verifies the challenge token returned by `/admin/auth/login` and a "
        "six-digit TOTP code for an Admin who has already enrolled TOTP. On "
        "success, creates a verified Admin session and returns the bearer "
        "access token used by protected Admin APIs."
    ),
    responses={
        401: {
            "description": (
                "Challenge token is invalid/expired, the account is no longer "
                "eligible, or the TOTP code is invalid (`INVALID_ADMIN_TOKEN` "
                "or `INVALID_AUTHENTICATION_CODE`)."
            )
        },
        403: {
            "description": (
                "The Admin account is locked or not active "
                "(`INACTIVE_ADMIN_ACCOUNT`)."
            )
        },
        422: {"description": "TOTP code is not exactly six digits."},
    },
)
async def verify_totp_login(
    request: Request,
    payload: AdminVerifyLoginRequest,
) -> ApiResponse[AdminAccessTokenData]:
    data = await admin_auth_service.verify_login(
        challenge_token=payload.challenge_token,
        otp_code=payload.otp_code,
        device_info=_device_info(request),
        request_id=_request_id(request),
    )
    return ApiResponse(
        success=True,
        data=data,
        message="Logged in successfully.",
    )
