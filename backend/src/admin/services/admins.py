import random
from typing import List

from beanie import PydanticObjectId

from src.admin.models import PlatformAdmin
from src.admin.schemas import (
    AdminCreateResponse,
    AdminDetailResponse,
    AdminUpdateRequest,
    AdminResetPasswordResponse,
)
from src.auth.services import get_password_hash
from src.exceptions import AppError
from src.audit.models import AuditLog
from src.models import utc_now


def generate_admin_username() -> str:
    allowed_chars = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
    return "admin-" + "".join(random.choice(allowed_chars) for _ in range(6))


async def get_unique_admin_username() -> str:
    while True:
        username = generate_admin_username()
        if not await PlatformAdmin.find_one(PlatformAdmin.username == username):
            return username


def generate_temp_password() -> str:
    uppercase = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    lowercase = "abcdefghijkmnpqrstuvwxyz"
    digits = "23456789"
    special = "@#$%&*!?"
    
    p_upper = random.choice(uppercase)
    p_lower = random.choice(lowercase)
    p_digit = random.choice(digits)
    p_special = random.choice(special)
    
    all_chars = uppercase + lowercase + digits + special
    p_rest = "".join(random.choice(all_chars) for _ in range(8))
    
    password_list = list(p_upper + p_lower + p_digit + p_special + p_rest)
    random.shuffle(password_list)
    return "".join(password_list)


async def log_audit_event(actor_id: PydanticObjectId, actor_type: str, action_type: str, detail: str):
    log = AuditLog(
        actor_id=actor_id,
        actor_type=actor_type,
        action_type=action_type,
        detail=detail,
        timestamp=utc_now(),
    )
    await log.insert()


async def create_admin(current_admin: PlatformAdmin) -> AdminCreateResponse:
    username = await get_unique_admin_username()
    temp_pass = generate_temp_password()
    pass_hash = get_password_hash(temp_pass)
    
    new_admin = PlatformAdmin(
        username=username,
        password_hash=pass_hash,
        role="operations_admin",
        twofa_method="totp",
        twofa_enabled=False,
        status="active",
    )
    await new_admin.insert()
    
    return AdminCreateResponse(
        id=str(new_admin.id),
        username=new_admin.username,
        role=new_admin.role,
        status=new_admin.status,
        temporary_password=temp_pass,
    )


def _to_detail_response(a: PlatformAdmin) -> AdminDetailResponse:
    return AdminDetailResponse(
        id=str(a.id),
        username=a.username,
        role=a.role or "operations_admin",
        status=a.status,
        twofa_enabled=a.twofa_enabled,
        totp_reset_requested=a.totp_reset_requested,
        totp_reset_requested_at=a.totp_reset_requested_at,
        password_reset_requested=a.password_reset_requested,
        password_reset_requested_at=a.password_reset_requested_at,
    )


async def list_admins(current_admin: PlatformAdmin) -> List[AdminDetailResponse]:
    admins = await PlatformAdmin.find_all().to_list()
    return [_to_detail_response(a) for a in admins]


async def get_admin(id: str, current_admin: PlatformAdmin) -> AdminDetailResponse:
    try:
        obj_id = PydanticObjectId(id)
    except Exception:
        raise AppError(status_code=404, message="Admin account not found.", error_code="ADMIN_NOT_FOUND")
        
    admin = await PlatformAdmin.get(obj_id)
    if not admin:
        raise AppError(status_code=404, message="Admin account not found.", error_code="ADMIN_NOT_FOUND")
        
    return _to_detail_response(admin)


async def update_admin(
    id: str,
    payload: AdminUpdateRequest,
    current_admin: PlatformAdmin,
) -> AdminDetailResponse:
    try:
        obj_id = PydanticObjectId(id)
    except Exception:
        raise AppError(status_code=404, message="Admin account not found.", error_code="ADMIN_NOT_FOUND")
        
    admin = await PlatformAdmin.get(obj_id)
    if not admin:
        raise AppError(status_code=404, message="Admin account not found.", error_code="ADMIN_NOT_FOUND")
        
    if payload.status == "locked":
        if not payload.reason or not payload.reason.strip():
            raise AppError(status_code=400, message="A reason is required.", error_code="REASON_REQUIRED")
        
        if admin.role == "super_admin" or admin.id == current_admin.id:
            raise AppError(status_code=403, message="Cannot lock a Super Admin account.", error_code="CANNOT_LOCK_SUPER_ADMIN")
            
        admin.status = "locked"
        await admin.save()
        
        await log_audit_event(
            actor_id=current_admin.id,
            actor_type="admin",
            action_type="account_suspended",
            detail=f"Account: {admin.username} (Admin), Reason: {payload.reason.strip()}",
        )
    elif payload.status == "active":
        if admin.status == "locked":
            admin.status = "active"
            await admin.save()
            
            await log_audit_event(
                actor_id=current_admin.id,
                actor_type="admin",
                action_type="account_reinstated",
                detail=f"Account: {admin.username} (Admin)",
            )
            
    return _to_detail_response(admin)


async def request_totp_reset(current_admin: PlatformAdmin) -> AdminDetailResponse:
    current_admin.totp_reset_requested = True
    current_admin.totp_reset_requested_at = utc_now()
    await current_admin.save()
    await log_audit_event(
        actor_id=current_admin.id,
        actor_type="admin",
        action_type="totp_reset_requested",
        detail=f"Requested TOTP reset for account: {current_admin.username}",
    )
    return _to_detail_response(current_admin)


async def request_password_reset(current_admin: PlatformAdmin) -> AdminDetailResponse:
    current_admin.password_reset_requested = True
    current_admin.password_reset_requested_at = utc_now()
    await current_admin.save()
    await log_audit_event(
        actor_id=current_admin.id,
        actor_type="admin",
        action_type="password_reset_requested",
        detail=f"Requested password reset for account: {current_admin.username}",
    )
    return _to_detail_response(current_admin)


async def list_reset_requests(current_admin: PlatformAdmin) -> List[AdminDetailResponse]:
    admins = await PlatformAdmin.find({
        "$or": [
            {"totp_reset_requested": True},
            {"password_reset_requested": True},
        ]
    }).to_list()
    return [_to_detail_response(a) for a in admins]


async def reset_admin_password(
    id: str,
    current_admin: PlatformAdmin,
) -> AdminResetPasswordResponse:
    try:
        obj_id = PydanticObjectId(id)
    except Exception:
        raise AppError(status_code=404, message="Admin account not found.", error_code="ADMIN_NOT_FOUND")
        
    admin = await PlatformAdmin.get(obj_id)
    if not admin:
        raise AppError(status_code=404, message="Admin account not found.", error_code="ADMIN_NOT_FOUND")
        
    if admin.role == "super_admin" and admin.id != current_admin.id:
        raise AppError(status_code=403, message="Cannot reset password for Super Admin.", error_code="CANNOT_RESET_SUPER_ADMIN")
        
    temp_pass = generate_temp_password()
    pass_hash = get_password_hash(temp_pass)
    
    admin.password_hash = pass_hash
    admin.password_reset_requested = False
    admin.password_reset_requested_at = None
    await admin.save()
    
    return AdminResetPasswordResponse(
        username=admin.username,
        temporary_password=temp_pass,
    )


async def reset_admin_2fa(
    id: str,
    current_admin: PlatformAdmin,
) -> AdminDetailResponse:
    try:
        obj_id = PydanticObjectId(id)
    except Exception:
        raise AppError(status_code=404, message="Admin account not found.", error_code="ADMIN_NOT_FOUND")
        
    admin = await PlatformAdmin.get(obj_id)
    if not admin:
        raise AppError(status_code=404, message="Admin account not found.", error_code="ADMIN_NOT_FOUND")
        
    if admin.role == "super_admin" and admin.id != current_admin.id:
        raise AppError(status_code=403, message="Cannot reset 2FA for Super Admin.", error_code="CANNOT_RESET_SUPER_ADMIN")
        
    admin.twofa_enabled = False
    admin.totp_secret = None
    admin.totp_reset_requested = False
    admin.totp_reset_requested_at = None
    await admin.save()
    
    await log_audit_event(
        actor_id=current_admin.id,
        actor_type="admin",
        action_type="2fa_reset",
        detail=f"Reset 2FA/TOTP secret for account: {admin.username} (Admin)",
    )
    
    return _to_detail_response(admin)


async def delete_admin(
    id: str,
    current_admin: PlatformAdmin,
) -> None:
    try:
        obj_id = PydanticObjectId(id)
    except Exception:
        raise AppError(status_code=404, message="Admin account not found.", error_code="ADMIN_NOT_FOUND")
        
    admin = await PlatformAdmin.get(obj_id)
    if not admin:
        raise AppError(status_code=404, message="Admin account not found.", error_code="ADMIN_NOT_FOUND")
        
    if admin.role == "super_admin" or admin.id == current_admin.id:
        raise AppError(status_code=403, message="Cannot delete a Super Admin account.", error_code="CANNOT_DELETE_SUPER_ADMIN")
        
    await admin.delete()
