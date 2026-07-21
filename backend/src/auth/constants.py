from enum import StrEnum


class ActorType(StrEnum):
    OWNER = "owner"
    INSTITUTION_ACCOUNT = "institution_account"
    PLATFORM_ADMIN = "platform_admin"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


SESSION_EXPIRY_DAYS = 30
