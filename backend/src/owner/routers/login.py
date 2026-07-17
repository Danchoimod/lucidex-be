from fastapi import APIRouter, Request, status

from src.auth.models import DeviceInfo
from src.owner.schemas import OwnerLoginRequest, OwnerLoginResponseData
from src.owner.services import owner_login_service
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/owner", tags=["Owner"])


@router.post(
    "/login",
    response_model=ApiResponse[OwnerLoginResponseData],
    status_code=status.HTTP_200_OK,
    summary="Login as an owner",
    description="Authenticates owner email and password, returning tokens and creating a session.",
)
async def login_owner(
    request: Request,
    payload: OwnerLoginRequest,
) -> ApiResponse[OwnerLoginResponseData]:
    user_agent = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    device_info = DeviceInfo(user_agent=user_agent, ip=ip)

    owner, access_token, refresh_token = await owner_login_service.login(
        email=payload.email,
        password=payload.password,
        device_info=device_info,
    )

    return ApiResponse[OwnerLoginResponseData](
        success=True,
        data=OwnerLoginResponseData(
            access_token=access_token,
            refresh_token=refresh_token,
            owner_id=str(owner.id),
            email=owner.email,
        ),
        message="Logged in successfully.",
        error_code=None,
    )
