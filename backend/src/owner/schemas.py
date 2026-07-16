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
