from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel


class InviteContext(BaseModel):
    invite_id: PydanticObjectId
    org_id: PydanticObjectId
    contact_email: str
    expires_at: datetime


class IssuedInvite(BaseModel):
    invite_id: PydanticObjectId
    raw_token: str
    expires_at: datetime
