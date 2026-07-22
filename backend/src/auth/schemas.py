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
    email: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@gmail.com"
            }
        }
    }
