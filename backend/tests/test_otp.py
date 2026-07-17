"""Tests for the standalone OTP module.

Beanie is initialized against an in-memory `mongomock_motor` database via
the `otp_test_database` fixture in `conftest.py`, so no real MongoDB
instance is required.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.otp import (
    OtpAlreadyUsedError,
    OtpCode,
    OtpCodeMismatchError,
    OtpExpiredError,
    OtpNotFoundError,
    OtpService,
    OtpType,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def service():
    return OtpService()


async def test_generate_otp_returns_numeric_string_of_requested_length():
    code_6 = OtpService.generate_otp(6)

    assert len(code_6) == 6 and code_6.isdigit()


async def test_create_otp_persists_record_and_returns_the_code(service):
    otp_code = await service.create_otp("user-1", "VERIFY_EMAIL")

    assert isinstance(otp_code, str)
    assert len(otp_code) == 6

    stored = await OtpCode.find(OtpCode.user_id == "user-1").first_or_none()
    assert stored is not None
    assert stored.otp_code == otp_code
    assert stored.type == OtpType.VERIFY_EMAIL
    assert stored.is_used is False


async def test_verify_valid_otp_succeeds(service):
    otp_code = await service.create_otp("user-2", "LOGIN")

    result = await service.verify_otp("user-2", otp_code, "LOGIN")

    assert result is True


async def test_verify_rejects_wrong_code(service):
    await service.create_otp("user-3", "RESET_PASSWORD")

    with pytest.raises(OtpCodeMismatchError):
        await service.verify_otp("user-3", "000000", "RESET_PASSWORD")


async def test_verify_rejects_unknown_user(service):
    with pytest.raises(OtpNotFoundError):
        await service.verify_otp("no-such-user", "1234", "LOGIN")


async def test_verify_rejects_expired_otp(service):
    otp_code = await service.create_otp("user-4", "VERIFY_EMAIL")

    # Force the stored document into the past to simulate expiry.
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    await OtpCode.find(OtpCode.user_id == "user-4").update(
        {"$set": {"expired_at": expired_time}}
    )

    with pytest.raises(OtpExpiredError):
        await service.verify_otp("user-4", otp_code, "VERIFY_EMAIL")


async def test_verify_rejects_already_used_otp(service):
    otp_code = await service.create_otp("user-5", "LOGIN")

    assert await service.verify_otp("user-5", otp_code, "LOGIN") is True

    with pytest.raises(OtpAlreadyUsedError):
        await service.verify_otp("user-5", otp_code, "LOGIN")


async def test_create_otp_invalidates_previous_active_otp(service):
    first_code = await service.create_otp("user-6", "LOGIN")
    second_code = await service.create_otp("user-6", "LOGIN")

    stored_first = await OtpCode.find(OtpCode.otp_code == first_code).first_or_none()
    assert stored_first.is_used is True

    # Verification always targets the newest OTP for the user, so
    # replaying the old code fails as a code mismatch (it's simply not
    # the code on file anymore).
    with pytest.raises(OtpCodeMismatchError):
        await service.verify_otp("user-6", first_code, "LOGIN")

    assert await service.verify_otp("user-6", second_code, "LOGIN") is True
