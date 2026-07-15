from typing import Literal

from beanie import Document
from pymongo import ASCENDING, IndexModel


class PlatformAdmin(Document):
    username: str
    password_hash: str
    twofa_method: Literal["email", "sms"] = "email"
    twofa_enabled: bool = False
    status: Literal["active", "locked"] = "active"

    class Settings:
        name = "platform_admins"
        indexes = [IndexModel([("username", ASCENDING)], unique=True)]
