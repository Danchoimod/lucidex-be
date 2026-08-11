import pytest
from types import SimpleNamespace
from beanie import PydanticObjectId

from src.exceptions import AppError
from src.invitation.constants import InviteStatus
from src.organization.services.institution_invite import InstitutionInviteService

ORG_ID = PydanticObjectId("507f1f77bcf86cd799439011")
INVITE_ID = PydanticObjectId("507f1f77bcf86cd799439013")


@pytest.fixture(autouse=True)
async def invitation_test_database():
    yield


@pytest.mark.asyncio
async def test_submit_password_rejects_used_token(monkeypatch):
    service = InstitutionInviteService()

    async def mock_validate_pending_invite(*args, **kwargs):
        raise AppError(
            status_code=400,
            message="Invalid or expired invitation link.",
            error_code="INVALID_INVITE",
        )

    monkeypatch.setattr(
        "src.organization.services.institution_invite.validate_pending_invite",
        mock_validate_pending_invite,
    )

    with pytest.raises(AppError) as exc_info:
        await service.submit_password(
            invite_token="used_token_sample",
            password="StrongPassword123!",
            confirm_password="StrongPassword123!",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "INVALID_INVITE"


@pytest.mark.asyncio
async def test_verify_otp_rejects_used_token(monkeypatch):
    service = InstitutionInviteService()

    async def mock_validate_pending_invite(*args, **kwargs):
        raise AppError(
            status_code=400,
            message="Invalid or expired invitation link.",
            error_code="INVALID_INVITE",
        )

    monkeypatch.setattr(
        "src.organization.services.institution_invite.validate_pending_invite",
        mock_validate_pending_invite,
    )

    with pytest.raises(AppError) as exc_info:
        await service.verify_otp(
            invite_token="used_token_sample",
            otp_code="123456",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "INVALID_INVITE"
