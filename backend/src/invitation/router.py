from fastapi import APIRouter

from src.invitation.schemas import (
    InstitutionAccountSetupData,
    SubmitInvitePasswordRequest,
)
from src.organization.services.invitation import submit_invite_password
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/institution/invite", tags=["Institution Invite"])


@router.post(
    "/password",
    response_model=ApiResponse[InstitutionAccountSetupData],
    summary="Create or update a pending institution account",
)
async def submit_password(
    payload: SubmitInvitePasswordRequest,
) -> ApiResponse[InstitutionAccountSetupData]:
    account = await submit_invite_password(
        invite_token=payload.invite_token,
        password=payload.password,
    )
    return ApiResponse(
        success=True,
        data=InstitutionAccountSetupData(
            account_id=str(account.id),
            status=account.status,
        ),
        message="Password submitted successfully.",
    )
