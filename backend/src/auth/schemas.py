from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    email: str
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@gmail.com",
                "password": "VerySecurePassword123!"
            }
        }
    }


class LoginResponseData(BaseModel):
    otp_token: str
    message: str = "Please verify the OTP code sent to your email to complete login."


class VerifyLoginOtpRequest(BaseModel):
    otp_token: str
    otp_code: str


class VerifyLoginOtpResponseData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    owner_id: str
    email: str


class ResendOtpRequest(BaseModel):
    email: str | None = None
    token: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@gmail.com",
                "token": "GeRnV7pLTjqVUaJmuCoKUmWfZaaJ1hoMNmQt4ZTjkgA"
            }
        }
    }


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "5986d3ab32561dd7dc03b61f6c53452e3db079b7444f5e545642e2d6cf5ba759"
            }
        }
    }


class RefreshTokenResponseData(BaseModel):
    access_token: str
    token_type: str = "bearer"
