from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class AdminLoginResponseData(BaseModel):
    requires_totp_setup: bool | None = None
    requires_totp: bool | None = None
    setup_token: str | None = None
    challenge_token: str | None = None
    totp_uri: str | None = None
    manual_entry_key: str | None = None
    qr_code: str | None = None


class AdminVerifySetupRequest(BaseModel):
    setup_token: str
    otp_code: str = Field(pattern=r"^\d{6}$")


class AdminVerifyLoginRequest(BaseModel):
    challenge_token: str
    otp_code: str = Field(pattern=r"^\d{6}$")


class AdminAccessTokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"
