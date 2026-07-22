from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class PasswordSubmitRequest(BaseModel):
    invite_token: str = Field(..., description="Raw invite token nhận được qua email")
    password: str = Field(..., description="Mật khẩu mới")
    confirm_password: str = Field(..., description="Xác nhận mật khẩu mới")

class PasswordSubmitResponseData(BaseModel):
    requires_otp: bool = True
    otp_expires_in_seconds: int = 300

# Bổ sung class bị thiếu ở đây nè:
class OtpVerifyRequest(BaseModel):
    invite_token: str = Field(..., description="Raw invite token của luồng kích hoạt")
    otp_code: str = Field(..., min_length=6, max_length=6, description="Mã OTP 6 chữ số nhận qua email")

class GenericApiResponse(BaseModel):
    success: bool = True
    data: Any = None
    message: str
    error_code: str | None = None