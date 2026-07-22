from pydantic import BaseModel, EmailStr, Field


class OwnerRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirm_password: str
    full_name: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@gmail.com",
                "password": "VerySecurePassword123!",
                "confirm_password": "VerySecurePassword123!",
                "full_name": "Nguyen Van A",
            }
        }
    }


class OwnerRegisterResponseData(BaseModel):
    id: str
    email: EmailStr
    status: str


class OwnerVerifyOtpResponseData(BaseModel):
    id: str
    email: EmailStr
    status: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class OwnerVerifyOtpRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=4, max_length=6)

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@gmail.com",
                "otp_code": "1234"
            }
        }
    }


class OwnerResendOtpRequest(BaseModel):
    email: EmailStr

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@gmail.com"
            }
        }
    }

from src.auth.schemas import (
    LoginRequest as OwnerLoginRequest,
    LoginResponseData as OwnerLoginResponseData,
    VerifyLoginOtpRequest as OwnerVerifyLoginOtpRequest,
    VerifyLoginOtpResponseData as OwnerVerifyLoginOtpResponseData,
)
