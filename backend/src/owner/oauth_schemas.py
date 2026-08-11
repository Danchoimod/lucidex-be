from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class OwnerGoogleAuthRequest(BaseModel):
    credential: str = Field(..., min_length=1)

    model_config = {"extra": "forbid"}


class OwnerGoogleAuthResponseData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    refresh_token_expires_at: datetime | None = None
    owner_id: str
    email: EmailStr
    full_name: str | None = None
