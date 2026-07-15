from typing import Literal

from beanie import Document, PydanticObjectId
from pymongo import ASCENDING, IndexModel


class InstitutionAccount(Document):
    org_id: PydanticObjectId
    username: str
    password_hash: str
    twofa_method: Literal["email", "sms"] = "email"
    twofa_enabled: bool = False
    status: Literal["active", "locked"] = "active"

    class Settings:
        name = "institution_accounts"
        indexes = [IndexModel([("username", ASCENDING)], unique=True)]
