from typing import Annotated, List

from fastapi import APIRouter, Depends, status

from src.admin.dependencies import require_admin, require_super_admin
from src.admin.models import PlatformAdmin
from src.admin.schemas import (
    AdminCreateResponse,
    AdminDetailResponse,
    AdminRequestStatusResponse,
    AdminUpdateRequest,
    AdminResetPasswordResponse,
)
from src.admin.services import admin_service

router = APIRouter(prefix="/admin/accounts")


@router.get(
    "/requests",
    response_model=List[AdminDetailResponse],
    status_code=status.HTTP_200_OK,
    tags=["Super Admin"],
    summary="Get list of pending reset requests from regular admins",
)
async def list_reset_requests(
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> List[AdminDetailResponse]:
    return await admin_service.list_reset_requests(current_admin)


@router.get(
    "/request-status",
    response_model=AdminRequestStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["Operations Admin"],
    summary="Get reset request status for current admin account",
)
async def get_request_status(
    current_admin: Annotated[PlatformAdmin, Depends(require_admin)],
) -> AdminRequestStatusResponse:
    return admin_service.get_request_status(current_admin)


@router.post(
    "/request-reset-totp",
    response_model=AdminDetailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Operations Admin"],
    summary="Request TOTP/2FA reset for current admin account",
)
async def request_totp_reset(
    current_admin: Annotated[PlatformAdmin, Depends(require_admin)],
) -> AdminDetailResponse:
    return await admin_service.request_totp_reset(current_admin)


@router.post(
    "/request-reset-password",
    response_model=AdminDetailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Operations Admin"],
    summary="Request password reset for current admin account",
)
async def request_password_reset(
    current_admin: Annotated[PlatformAdmin, Depends(require_admin)],
) -> AdminDetailResponse:
    return await admin_service.request_password_reset(current_admin)


@router.post(
    "",
    response_model=AdminCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Super Admin"],
)
async def create_admin(
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> AdminCreateResponse:
    return await admin_service.create_admin(current_admin)


@router.get(
    "",
    response_model=List[AdminDetailResponse],
    status_code=status.HTTP_200_OK,
    tags=["Super Admin"],
)
async def list_admins(
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> List[AdminDetailResponse]:
    return await admin_service.list_admins(current_admin)


@router.get(
    "/{id}",
    response_model=AdminDetailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Super Admin"],
)
async def get_admin(
    id: str,
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> AdminDetailResponse:
    return await admin_service.get_admin(id, current_admin)


@router.put(
    "/{id}",
    response_model=AdminDetailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Super Admin"],
)
async def update_admin(
    id: str,
    payload: AdminUpdateRequest,
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> AdminDetailResponse:
    return await admin_service.update_admin(id, payload, current_admin)


@router.post(
    "/{id}/reset-password",
    response_model=AdminResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    tags=["Super Admin"],
)
async def reset_admin_password(
    id: str,
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> AdminResetPasswordResponse:
    return await admin_service.reset_admin_password(id, current_admin)


@router.post(
    "/{id}/reset-2fa",
    response_model=AdminDetailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Super Admin"],
    summary="Reset TOTP 2FA for Admin account",
)
async def reset_admin_2fa(
    id: str,
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> AdminDetailResponse:
    return await admin_service.reset_admin_2fa(id, current_admin)


@router.post(
    "/{id}/reject-reset-totp",
    response_model=AdminDetailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Super Admin"],
    summary="Reject TOTP 2FA reset request for Admin account",
)
async def reject_admin_2fa_reset(
    id: str,
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> AdminDetailResponse:
    return await admin_service.reject_totp_reset(id, current_admin)


@router.post(
    "/{id}/reject-reset-password",
    response_model=AdminDetailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Super Admin"],
    summary="Reject password reset request for Admin account",
)
async def reject_admin_password_reset(
    id: str,
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> AdminDetailResponse:
    return await admin_service.reject_password_reset(id, current_admin)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Super Admin"],
)
async def delete_admin(
    id: str,
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
):
    await admin_service.delete_admin(id, current_admin)
