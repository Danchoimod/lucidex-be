from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class OwnerRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirm_password: str
    full_name: str | None = None
    phone: str | None = None

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
    refresh_token_expires_at: datetime | None = None
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



class DefaultLinkSettingsData(BaseModel):
    default_consent_mode: str | None = None
    default_max_access_count: int | None = None
    default_expiry_hours: int | None = None
    default_allowed_org_ids: list[str] = Field(default_factory=list)


class PatchLinkSettingsRequest(BaseModel):
    default_consent_mode: str | None = Field(default=None, description="Default consent mode or null to reset.")
    default_max_access_count: int | None = Field(default=None, ge=1, description="Default maximum access count (>= 1).")
    default_expiry_hours: int | None = Field(default=None, ge=1, description="Default expiry hours (>= 1).")
    default_allowed_org_ids: list[str] | None = Field(default=None, description="Default allowed verifier org IDs.")

    model_config = {"extra": "forbid"}


GetLinkSettingsResponse = DefaultLinkSettingsData
PatchLinkSettingsResponse = DefaultLinkSettingsData

