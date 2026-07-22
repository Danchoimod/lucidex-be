from fastapi import APIRouter, Request, status

from src.auth.models import DeviceInfo
from src.owner.oauth_schemas import (
    OwnerGoogleAuthRequest,
    OwnerGoogleAuthResponseData,
)
from src.owner.services import owner_oauth_auth_service
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/owner/auth", tags=["Owner"])


@router.post(
    "/google",
    response_model=ApiResponse[OwnerGoogleAuthResponseData],
    status_code=status.HTTP_200_OK,
    summary="Continue as an owner with Google",
    description=(
        "Sign up or log in an Owner using a Google ID token.\n\n"
        "### Cách lấy token\n\n"
        "Hãy nhấn [Open Google OAuth QA page]"
        "(/api/v1/owner/auth/google/test)."
    ),
    responses={
        401: {"description": "Invalid or expired Google ID token."},
        403: {"description": "Google email is not verified."},
        409: {"description": "Google identity conflicts with the existing account."},
        503: {"description": "Google OAuth is not configured or unavailable."},
    },
    openapi_extra={"security": []},
)
async def login_owner_with_google(
    request: Request,
    payload: OwnerGoogleAuthRequest,
) -> ApiResponse[OwnerGoogleAuthResponseData]:
    device_info = DeviceInfo(
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    owner, access_token, refresh_token = (
        await owner_oauth_auth_service.login_with_google(
            credential=payload.credential,
            device_info=device_info,
            request_id=getattr(request.state, "request_id", None),
        )
    )
    return ApiResponse[OwnerGoogleAuthResponseData](
        success=True,
        data=OwnerGoogleAuthResponseData(
            access_token=access_token,
            refresh_token=refresh_token,
            owner_id=str(owner.id),
            email=owner.email,
        ),
        message="Logged in successfully.",
        error_code=None,
    )
