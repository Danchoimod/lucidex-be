from typing import Annotated, List

from fastapi import APIRouter, Depends, status

from src.admin.dependencies import require_super_admin
from src.admin.models import PlatformAdmin
from src.admin.schemas import (
    AdminCreateResponse,
    AdminDetailResponse,
    AdminUpdateRequest,
    AdminResetPasswordResponse,
)
from src.admin.services import admin_service

router = APIRouter(prefix="/admin/accounts", tags=["Super Admin"])


@router.post(
    "",
    response_model=AdminCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin(
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> AdminCreateResponse:
    return await admin_service.create_admin(current_admin)


@router.get(
    "",
    response_model=List[AdminDetailResponse],
    status_code=status.HTTP_200_OK,
)
async def list_admins(
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> List[AdminDetailResponse]:
    return await admin_service.list_admins(current_admin)


@router.get(
    "/{id}",
    response_model=AdminDetailResponse,
    status_code=status.HTTP_200_OK,
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
    summary="Reset TOTP 2FA for Admin account",
)
async def reset_admin_2fa(
    id: str,
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
) -> AdminDetailResponse:
    return await admin_service.reset_admin_2fa(id, current_admin)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_admin(
    id: str,
    current_admin: Annotated[PlatformAdmin, Depends(require_super_admin)],
):
    await admin_service.delete_admin(id, current_admin)
