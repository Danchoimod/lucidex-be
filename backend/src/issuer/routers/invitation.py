"""Invitation router for issuer organization activation flow."""

from fastapi import APIRouter, status

from src.issuer.services import issuer_invite_service
from src.organization.institution_invite_schemas import (
    GenericApiResponse,
    OtpVerifyRequest,
    PasswordSubmitRequest,
)

router = APIRouter()


@router.post(
    "/invites/password",
    response_model=GenericApiResponse,
    status_code=status.HTTP_200_OK,
    summary="[Issuer] Set password and request activation OTP",
)
async def submit_issuer_password(payload: PasswordSubmitRequest) -> GenericApiResponse:
    data = await issuer_invite_service.submit_password(
        invite_token=payload.invite_token,
        password=payload.password,
        confirm_password=payload.confirm_password,
    )
    return GenericApiResponse(
        success=True,
        data=data,
        message="Password set successfully. Please check your email for the activation OTP code.",
    )


@router.post(
    "/invites/verify-otp",
    response_model=GenericApiResponse,
    status_code=status.HTTP_200_OK,
    summary="[Issuer] Verify OTP and activate issuer organization account",
)
async def verify_issuer_otp(payload: OtpVerifyRequest) -> GenericApiResponse:
    data = await issuer_invite_service.verify_otp(
        invite_token=payload.invite_token,
        otp_code=payload.otp_code,
    )
    return GenericApiResponse(
        success=True,
        data=data,
        message="Organization account activated successfully.",
    )
