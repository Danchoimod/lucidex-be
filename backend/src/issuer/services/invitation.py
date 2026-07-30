"""Issuer invitation service logic."""

from typing import Any

from src.organization.services.institution_invite import institution_invite_service


class IssuerInviteService:
    """Service to handle issuer institution invitations and activation."""

    async def submit_password(
        self,
        invite_token: str,
        password: str,
        confirm_password: str,
    ) -> Any:
        """Submit password to accept invitation and request OTP."""
        return await institution_invite_service.submit_password(
            invite_token=invite_token,
            password=password,
            confirm_password=confirm_password,
        )

    async def verify_otp(
        self,
        invite_token: str,
        otp_code: str,
    ) -> Any:
        """Verify activation OTP and activate issuer organization account."""
        return await institution_invite_service.verify_otp(
            invite_token=invite_token,
            otp_code=otp_code,
        )


issuer_invite_service = IssuerInviteService()
