from pydantic import BaseModel, EmailStr


class OAuthIdentity(BaseModel):
    provider: str
    provider_subject: str
    email: EmailStr
    display_name: str | None = None
    avatar_url: str | None = None
