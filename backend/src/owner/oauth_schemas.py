from pydantic import BaseModel, EmailStr, Field


class OwnerGoogleAuthRequest(BaseModel):
    credential: str = Field(..., min_length=1)

    model_config = {"extra": "forbid"}


class OwnerGoogleAuthResponseData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    owner_id: str
    email: EmailStr
