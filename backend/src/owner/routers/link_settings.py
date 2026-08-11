from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.auth.dependencies import require_current_actor
from src.owner.models import Owner
from src.owner.schemas import (
    GetLinkSettingsResponse,
    PatchLinkSettingsRequest,
    PatchLinkSettingsResponse,
)
from src.owner.services import link_settings as link_settings_service
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/owner/link-settings", tags=["Owner - Link Settings"])


@router.get(
    "",
    response_model=ApiResponse[GetLinkSettingsResponse],
    status_code=status.HTTP_200_OK,
    summary="[Owner] Get Default Link Settings",
    description="Retrieve the authenticated owner's saved default consent settings.",
)
async def get_link_settings(
    actor_info: Annotated[tuple, Depends(require_current_actor)],
) -> ApiResponse[GetLinkSettingsResponse]:
    actor, _, _ = actor_info
    owner: Owner = actor  # type: ignore

    data = await link_settings_service.get_link_settings(owner)
    return ApiResponse[GetLinkSettingsResponse](
        success=True,
        data=data,
        message="Default link settings retrieved.",
        error_code=None,
    )


@router.patch(
    "",
    response_model=ApiResponse[PatchLinkSettingsResponse],
    status_code=status.HTTP_200_OK,
    summary="[Owner] Update Default Link Settings",
    description="Update the authenticated owner's default consent settings (partial update).",
)
async def update_link_settings(
    payload: PatchLinkSettingsRequest,
    actor_info: Annotated[tuple, Depends(require_current_actor)],
) -> ApiResponse[PatchLinkSettingsResponse]:
    actor, _, _ = actor_info
    owner: Owner = actor  # type: ignore

    data = await link_settings_service.update_link_settings(owner, payload)
    return ApiResponse[PatchLinkSettingsResponse](
        success=True,
        data=data,
        message="Default link settings updated.",
        error_code=None,
    )
