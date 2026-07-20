from enum import StrEnum


class InviteStatus(StrEnum):
    PENDING = "pending"
    USED = "used"
    REVOKED = "revoked"
