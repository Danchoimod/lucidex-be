from pydantic import BaseModel, EmailStr, Field


class OwnerRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirm_password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@gmail.com",
                "password": "VerySecurePassword123!",
                "confirm_password": "VerySecurePassword123!"
            }
        }
    }


class OwnerRegisterResponseData(BaseModel):
    id: str
    email: EmailStr
    status: str


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

class OwnerLoginRequest(BaseModel):
    email: EmailStr
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@gmail.com",
                "password": "VerySecurePassword123!"
            }
        }
    }


class OwnerLoginResponseData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    owner_id: str
    email: EmailStr
