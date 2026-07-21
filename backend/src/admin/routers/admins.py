import random
from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from beanie import PydanticObjectId

from src.admin.dependencies import require_super_admin
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

router = APIRouter(prefix="/admin/accounts", tags=["Admin Accounts"])


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


@router.post(
    "",
    response_model=AdminCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin(
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> AdminCreateResponse:
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


@router.get(
    "",
    response_model=List[AdminDetailResponse],
    status_code=status.HTTP_200_OK,
)
async def list_admins(
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> List[AdminDetailResponse]:
    admins = await PlatformAdmin.find_all().to_list()
    return [
        AdminDetailResponse(
            id=str(a.id),
            username=a.username,
            role=a.role or "operations_admin",
            status=a.status,
            twofa_enabled=a.twofa_enabled,
        )
        for a in admins
    ]


@router.get(
    "/{id}",
    response_model=AdminDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_admin(
    id: str,
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> AdminDetailResponse:
    try:
        obj_id = PydanticObjectId(id)
    except Exception:
        raise AppError(status_code=404, message="Admin account not found.", error_code="ADMIN_NOT_FOUND")
        
    admin = await PlatformAdmin.get(obj_id)
    if not admin:
        raise AppError(status_code=404, message="Admin account not found.", error_code="ADMIN_NOT_FOUND")
        
    return AdminDetailResponse(
        id=str(admin.id),
        username=admin.username,
        role=admin.role or "operations_admin",
        status=admin.status,
        twofa_enabled=admin.twofa_enabled,
    )


@router.put(
    "/{id}",
    response_model=AdminDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def update_admin(
    id: str,
    payload: AdminUpdateRequest,
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
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
            
    return AdminDetailResponse(
        id=str(admin.id),
        username=admin.username,
        role=admin.role or "operations_admin",
        status=admin.status,
        twofa_enabled=admin.twofa_enabled,
    )


@router.post(
    "/{id}/reset-password",
    response_model=AdminResetPasswordResponse,
    status_code=status.HTTP_200_OK,
)
async def reset_admin_password(
    id: str,
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> AdminResetPasswordResponse:
    try:
        obj_id = PydanticObjectId(id)
    except Exception:
        raise AppError(status_code=404, message="Admin account not found.", error_code="ADMIN_NOT_FOUND")
        
    admin = await PlatformAdmin.get(obj_id)
    if not admin:
        raise AppError(status_code=404, message="Admin account not found.", error_code="ADMIN_NOT_FOUND")
        
    if admin.role == "super_admin" or admin.id == current_admin.id:
        raise AppError(status_code=403, message="Cannot reset password for Super Admin.", error_code="CANNOT_RESET_SUPER_ADMIN")
        
    temp_pass = generate_temp_password()
    pass_hash = get_password_hash(temp_pass)
    
    admin.password_hash = pass_hash
    await admin.save()
    
    return AdminResetPasswordResponse(
        username=admin.username,
        temporary_password=temp_pass,
    )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_admin(
    id: str,
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
):
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
