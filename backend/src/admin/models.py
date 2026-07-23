from typing import Literal

from beanie import Document
from pymongo import ASCENDING, IndexModel


class PlatformAdmin(Document):
    username: str
    password_hash: str
    role: Literal["super_admin", "operations_admin"] | None = None
    twofa_method: Literal["email", "sms", "totp"] = "totp"
    twofa_enabled: bool = False
    totp_secret: str | None = None
    status: Literal["active", "locked"] = "active"
    totp_reset_requested: bool = False
    password_reset_requested: bool = False

    class Settings:
        name = "platform_admins"
        indexes = [IndexModel([("username", ASCENDING)], unique=True)]
