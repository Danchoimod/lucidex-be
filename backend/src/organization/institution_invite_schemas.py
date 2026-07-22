from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class PasswordSubmitRequest(BaseModel):
    invite_token: str = Field(..., description="Raw invite token received via email")
    password: str = Field(..., description="New password")
    confirm_password: str = Field(..., description="Confirm new password")

class PasswordSubmitResponseData(BaseModel):
    requires_otp: bool = True
    otp_expires_in_seconds: int = 300

# Bổ sung class bị thiếu ở đây nè:
class OtpVerifyRequest(BaseModel):
    invite_token: str = Field(..., description="Raw invite token for activation flow")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code received via email")

class GenericApiResponse(BaseModel):
    success: bool = True
    data: Any = None
    message: str
    error_code: str | None = None