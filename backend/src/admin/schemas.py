from pydantic import BaseModel, ConfigDict, Field


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


class AdminCreateResponse(BaseModel):
    id: str
    username: str
    role: str
    status: str
    temporary_password: str


class AdminDetailResponse(BaseModel):
    id: str
    username: str
    role: str
    status: str
    twofa_enabled: bool
    totp_reset_requested: bool = False
    password_reset_requested: bool = False


class AdminUpdateRequest(BaseModel):
    status: str = Field(pattern=r"^(active|locked)$")
    reason: str | None = None



class AdminResetPasswordResponse(BaseModel):
    username: str
    temporary_password: str


class RejectOrganizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None

