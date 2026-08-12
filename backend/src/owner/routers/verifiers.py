from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.auth.dependencies import require_current_actor
from src.exceptions import AppError
from src.owner.schemas import VerifierItemResponse
from src.owner.services import verifiers as verifiers_service
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/owner/verifiers-list", tags=["Owner"])


@router.get(
    "",
    response_model=ApiResponse[list[VerifierItemResponse]],
    status_code=status.HTTP_200_OK,
    summary="[Owner] Get List of Verifiers",
    description="Retrieve list of approved verifier organizations containing id and name.",
)
async def get_verifiers(
    actor_info: Annotated[tuple, Depends(require_current_actor)],
) -> ApiResponse[list[VerifierItemResponse]]:
    actor, _, actor_type = actor_info
    if actor_type != "owner":
        raise AppError(
            status_code=403,
            message="Only owner accounts can access this resource.",
            error_code="FORBIDDEN",
        )

    data = await verifiers_service.list_verifiers()
    return ApiResponse[list[VerifierItemResponse]](
        success=True,
        data=data,
        message="Verifiers list retrieved successfully.",
        error_code=None,
    )

