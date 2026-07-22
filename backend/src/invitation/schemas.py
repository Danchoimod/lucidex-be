from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from src.organization.constants import AccountStatus


class InviteContext(BaseModel):
    invite_id: PydanticObjectId
    org_id: PydanticObjectId
    contact_email: str
    expires_at: datetime


class IssuedInvite(BaseModel):
    invite_id: PydanticObjectId
    raw_token: str
    expires_at: datetime


class SubmitInvitePasswordRequest(BaseModel):
    invite_token: str = Field(min_length=1)
    password: str = Field(min_length=8)


class InstitutionAccountSetupData(BaseModel):
    account_id: str
    status: AccountStatus
