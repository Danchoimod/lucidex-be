from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class InstitutionAccount(Document):
    org_id: PydanticObjectId
    username: str
    password_hash: str
    role_ids: list[PydanticObjectId] = Field(default_factory=list)
    twofa_method: Literal["email", "sms"] = "email"
    twofa_enabled: bool = False
    status: Literal["active", "locked"] = "active"

    class Settings:
        name = "institution_accounts"
        indexes = [IndexModel([("username", ASCENDING)], unique=True)]
