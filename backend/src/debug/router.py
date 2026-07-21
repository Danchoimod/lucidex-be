from fastapi import APIRouter, status

from src.auth.models import Session
from src.debug.schemas import DeleteUserDebugRequest, DeleteUserDebugResponse
from src.invitation.models import InviteLink
from src.organization.models import InstitutionAccount, Organization
from src.otp.models import OtpCode
from src.owner.models import Owner
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/debug", tags=["Debug / Testing"])


@router.post(
    "/delete-user",
    response_model=ApiResponse[DeleteUserDebugResponse],
    status_code=status.HTTP_200_OK,
    summary="[DEBUG] Delete user by email",
    description="Deletes matching user records from owner and organization/institution_accounts tables for rapid testing.",
)
async def delete_user_debug(
    payload: DeleteUserDebugRequest,
) -> ApiResponse[DeleteUserDebugResponse]:
    normalized_email = payload.email.strip().lower()
    deleted_ids = []

    # 1. Delete matching Owners
    owners = await Owner.find(
        {"email": {"$regex": f"^{normalized_email}$", "$options": "i"}}
    ).to_list()
    for o in owners:
        deleted_ids.append(o.id)
        await o.delete()

    # 2. Delete matching InstitutionAccounts
    inst_accounts = await InstitutionAccount.find(
        {"email": {"$regex": f"^{normalized_email}$", "$options": "i"}}
    ).to_list()
    for ia in inst_accounts:
        deleted_ids.append(ia.id)
        await ia.delete()

    # 3. Delete matching Organizations
    orgs = await Organization.find(
        {"contact_email": {"$regex": f"^{normalized_email}$", "$options": "i"}}
    ).to_list()
    for org in orgs:
        deleted_ids.append(org.id)
        await org.delete()

    # 4. Delete matching InviteLinks
    invites = await InviteLink.find(
        {"contact_email": {"$regex": f"^{normalized_email}$", "$options": "i"}}
    ).to_list()
    for inv in invites:
        await inv.delete()

    # 5. Clean up linked Sessions & OtpCodes
    sess_count = 0
    otp_count = 0
    for uid in deleted_ids:
        s_res = await Session.find({"actor_id": uid}).delete()
        if s_res and hasattr(s_res, "deleted_count"):
            sess_count += s_res.deleted_count
        o_res = await OtpCode.find({"user_id": str(uid)}).delete()
        if o_res and hasattr(o_res, "deleted_count"):
            otp_count += o_res.deleted_count

    data = DeleteUserDebugResponse(
        deleted_owners=len(owners),
        deleted_institution_accounts=len(inst_accounts),
        deleted_organizations=len(orgs),
        deleted_invites=len(invites),
        deleted_sessions=sess_count,
        deleted_otps=otp_count,
    )

    return ApiResponse[DeleteUserDebugResponse](
        success=True,
        data=data,
        message=f"User with email '{payload.email}' has been completely deleted.",
        error_code=None,
    )
