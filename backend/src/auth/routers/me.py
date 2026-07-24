from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.admin.models import PlatformAdmin
from src.auth.dependencies import require_current_actor
from src.auth.models import Session
from src.auth.schemas import MeResponseData
from src.auth.services import me_service
from src.organization.models import InstitutionAccount
from src.owner.models import Owner
from src.schemas import ApiResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get(
    "/me",
    response_model=ApiResponse[MeResponseData],
    status_code=status.HTTP_200_OK,
    summary="Get current user profile (Me)",
    description="Returns profile info for the currently authenticated actor (Platform Admin, Owner, or Institution Account) using the Bearer access token.",
)
async def get_me(
    actor_info: Annotated[
        tuple[PlatformAdmin | Owner | InstitutionAccount, Session, str],
        Depends(require_current_actor),
    ],
) -> ApiResponse[MeResponseData]:
    data = await me_service.get_me(actor_info)
    return ApiResponse[MeResponseData](
        success=True,
        data=data,
        message="Profile fetched successfully.",
        error_code=None,
    )
