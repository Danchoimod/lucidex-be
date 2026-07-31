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


from src.debug.vnpt_models import (
    VnptEkycConfig,
    VnptEkycConfigRequest,
    VnptEkycConfigResponse,
)


@router.get(
    "/vnpt-ekyc-config",
    response_model=ApiResponse[VnptEkycConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="[DEBUG] Get VNPT eKYC credentials config",
)
async def get_vnpt_ekyc_config() -> ApiResponse[VnptEkycConfigResponse]:
    config = await VnptEkycConfig.find_one({"config_key": "global_vnpt_config"})
    if not config:
        # Nếu chưa lưu cấu hình trong DB thì các trường sẽ trả về None (null)
        data = VnptEkycConfigResponse(
            access_token=None,
            token_id=None,
            token_key=None,
            public_key_ca=None,
        )
    else:
        data = VnptEkycConfigResponse(
            access_token=config.access_token,
            token_id=config.token_id,
            token_key=config.token_key,
            public_key_ca=config.public_key_ca,
        )

    return ApiResponse[VnptEkycConfigResponse](
        success=True,
        data=data,
        message="VNPT eKYC Config retrieved successfully.",
        error_code=None,
    )



@router.post(
    "/vnpt-ekyc-config",
    response_model=ApiResponse[VnptEkycConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="[DEBUG] Create or Update VNPT eKYC credentials config (Fixed Single Document)",
)
@router.patch(
    "/vnpt-ekyc-config",
    response_model=ApiResponse[VnptEkycConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="[DEBUG] Update VNPT eKYC credentials config (Fixed Single Document)",
)
async def save_vnpt_ekyc_config(
    payload: VnptEkycConfigRequest,
) -> ApiResponse[VnptEkycConfigResponse]:
    config = await VnptEkycConfig.find_one({"config_key": "global_vnpt_config"})
    if config:
        # Cập nhật duy nhất 1 bản ghi cố định
        config.access_token = payload.access_token
        config.token_id = payload.token_id
        config.token_key = payload.token_key
        config.public_key_ca = payload.public_key_ca
        await config.save()
    else:
        # Tạo mới duy nhất bản ghi đầu tiên
        config = VnptEkycConfig(
            config_key="global_vnpt_config",
            access_token=payload.access_token,
            token_id=payload.token_id,
            token_key=payload.token_key,
            public_key_ca=payload.public_key_ca,
        )
        await config.insert()

    data = VnptEkycConfigResponse(
        access_token=config.access_token,
        token_id=config.token_id,
        token_key=config.token_key,
        public_key_ca=config.public_key_ca,
    )

    return ApiResponse[VnptEkycConfigResponse](
        success=True,
        data=data,
        message="VNPT eKYC Config saved/updated successfully.",
        error_code=None,
    )

