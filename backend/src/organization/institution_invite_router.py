"""Institution invite module routes."""

from __future__ import annotations

from fastapi import APIRouter, status

from src.organization.institution_invite_schemas import (
    GenericApiResponse,
    OtpVerifyRequest,
    PasswordSubmitRequest,
)
from src.organization.services.institution_invite import institution_invite_service

# Khai báo router riêng biệt, đặt tên là router luôn cho chuẩn convention
router = APIRouter(prefix="/institution-invites", tags=["Institution Invites"])


@router.post(
    "/password",
    response_model=GenericApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Thiết lập/cập nhật mật khẩu tài khoản tổ chức và yêu cầu gửi OTP",
)
async def submit_password(payload: PasswordSubmitRequest) -> GenericApiResponse:
    data = await institution_invite_service.submit_password(
        invite_token=payload.invite_token,
        password=payload.password,
        confirm_password=payload.confirm_password,
    )
    return GenericApiResponse(
        success=True,
        data=data,
        message="Mật khẩu đã được thiết lập. Vui lòng kiểm tra email để nhận mã OTP kích hoạt.",
    )


@router.post(
    "/verify-otp",
    response_model=GenericApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Xác thực OTP và hoàn tất kích hoạt tài khoản tổ chức",
)
async def verify_otp(payload: OtpVerifyRequest) -> GenericApiResponse:
    data = await institution_invite_service.verify_otp(
        invite_token=payload.invite_token,
        otp_code=payload.otp_code,
    )
    return GenericApiResponse(
        success=True,
        data=data,
        message="Tài khoản tổ chức đã được kích hoạt thành công.",
    )